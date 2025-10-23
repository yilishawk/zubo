import requests
import re
import os
from urllib.parse import urlparse
from datetime import datetime

URLS = [
    "https://fy.188766.xyz/?ip=&bconly=true&mima=mianfeidehaimaiqian&json=true",
    "https://txt.gt.tc/users/HKTV.txt?i=1",
    "http://iptv.4666888.xyz/FYTV.txt",
    "https://raw.githubusercontent.com/develop202/migu_video/main/interface.txt",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/125.0 Safari/537.36",
    "Referer": "https://www.google.com",
    "Accept": "*/*",
}

def normalize_name(name):
    name = name.strip().upper()
    name = re.sub(r"[^A-Z0-9]", "", name)
    if name.startswith("CCTV"):
        name = "cctv" + re.sub(r"\D", "", name.replace("CCTV", ""))
    else:
        name = name.lower()
    return name

def fetch_url(url):
    print(f"📡 Fetching: {url}")
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"❌ Failed: {url} ({e})")
        return ""

def parse_m3u(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    result = []
    name = None
    for line in lines:
        if line.startswith("#EXTINF:"):
            m = re.search(r",(.+)", line)
            if m:
                name = m.group(1)
        elif line.startswith("http"):
            if name:
                result.append((name, line))
                name = None
            else:
                m = re.search(r"(CCTV[ -]?\d+.*)", line, re.I)
                cname = m.group(1) if m else "unknown"
                result.append((cname, line))
    return result

def domain_available(urls):
    checked = {}
    valid = []
    for cname, link in urls:
        domain = urlparse(link).netloc
        if domain in checked:
            if checked[domain]:
                valid.append((cname, link))
            continue
        try:
            resp = requests.head(link, headers=HEADERS, timeout=5)
            ok = resp.status_code < 400
            checked[domain] = ok
            if ok:
                print(f"✅ Domain OK: {domain}")
                valid.append((cname, link))
            else:
                print(f"⚠️ Domain Bad: {domain}")
        except Exception:
            checked[domain] = False
            print(f"❌ Domain Down: {domain}")
    return valid

def main():
    all_channels = []
    for url in URLS:
        text = fetch_url(url)
        if text:
            all_channels += parse_m3u(text)

    normalized = [(normalize_name(n), l) for n, l in all_channels]
    filtered = domain_available(normalized)

    merged = {}
    for cname, link in filtered:
        merged.setdefault(cname, []).append(link)

    with open("merged.txt", "w", encoding="utf-8") as f:
        f.write(f"# Auto generated IPTV list\n")
        f.write(f"# Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")
        for cname, links in merged.items():
            for link in links:
                f.write(f"{cname},{link}\n")

    print(f"✅ Merged {len(merged)} channels saved to merged.txt")

    os.system('git config --global user.name "github-actions[bot]"')
    os.system('git config --global user.email "github-actions[bot]@users.noreply.github.com"')
    os.system("git add merged.txt")
    os.system('git commit -m "Auto update merged.txt" || echo "No changes"')
    os.system("git push")

if __name__ == "__main__":
    main()
