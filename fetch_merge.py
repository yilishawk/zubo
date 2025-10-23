import requests
import re
import os
from urllib.parse import urlparse

# 四个直播源地址
URLS = [
    "https://fy.188766.xyz/?ip=&bconly=true&mima=mianfeidehaimaiqian&json=true",
    "https://txt.gt.tc/users/HKTV.txt?i=1",
    "http://iptv.4666888.xyz/FYTV.txt",
    "https://raw.githubusercontent.com/develop202/migu_video/main/interface.txt",
]

# 频道名映射清洗规则
def normalize_name(name):
    name = name.strip().upper()
    name = re.sub(r"[^A-Z0-9]", "", name)
    # 特殊映射
    name = name.replace("CCTV", "CCTV")
    if name.startswith("CCTV"):
        name = "cctv" + re.sub(r"\D", "", name.replace("CCTV", ""))  # CCTV1综合 → cctv1
    else:
        name = name.lower()
    return name

def fetch_url(url):
    print(f"📡 Fetching: {url}")
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        text = r.text
        return text
    except Exception as e:
        print(f"❌ Failed: {url} ({e})")
        return ""

def parse_m3u(text):
    """解析M3U或TXT格式"""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    result = []
    name = None
    for line in lines:
        if line.startswith("#EXTINF:"):
            match = re.search(r",(.+)", line)
            if match:
                name = match.group(1)
        elif line.startswith("http"):
            if name:
                result.append((name, line))
                name = None
            else:
                # 有些TXT格式直接就是链接+名字
                m = re.search(r"(CCTV[ -]?\d+.*)", line, re.I)
                cname = m.group(1) if m else "unknown"
                result.append((cname, line))
    return result

def domain_available(urls):
    """只检测一个域名"""
    checked = {}
    valid = []
    for _, link in urls:
        domain = urlparse(link).netloc
        if domain in checked:
            if checked[domain]:
                valid.append((_, link))
            continue
        try:
            resp = requests.head(link, timeout=5)
            ok = resp.status_code < 400
            checked[domain] = ok
            if ok:
                print(f"✅ Domain OK: {domain}")
                valid.append((_, link))
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

    # 标准化频道名
    normalized = []
    for name, link in all_channels:
        normalized.append((normalize_name(name), link))

    # 测试域名并过滤
    filtered = domain_available(normalized)

    # 按频道归类
    merged = {}
    for cname, link in filtered:
        merged.setdefault(cname, []).append(link)

    # 写入txt
    with open("merged.txt", "w", encoding="utf-8") as f:
        for cname, links in merged.items():
            for link in links:
                f.write(f"{cname},{link}\n")

    print(f"✅ Merged {len(merged)} channels saved to merged.txt")

    # GitHub Action: 推送到仓库
    os.system('git config --global user.name "github-actions[bot]"')
    os.system('git config --global user.email "github-actions[bot]@users.noreply.github.com"')
    os.system("git add merged.txt")
    os.system('git commit -m "Auto update merged.txt" || echo "No changes"')
    os.system("git push")

if __name__ == "__main__":
    main()
