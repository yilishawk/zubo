#!/usr/bin/env python3
import requests
import json
import re
from collections import defaultdict
from typing import List, Tuple, Dict

def fetch_content(url: str) -> str:
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.text
    except:
        return ""

def parse_json(content: str) -> List[Tuple[str, str]]:
    try:
        data = json.loads(content)
        streams = []
        if isinstance(data, list):
            for item in data:
                name = item.get('name', 'Unknown')
                url = item.get('url', '')
                if url and '.m3u8' in url:
                    streams.append((name, url))
        return streams
    except:
        return []

def parse_m3u(content: str, base_url: str = "") -> List[Tuple[str, str]]:
    streams = []
    lines = content.splitlines()
    current_name = ""
    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF:"):
            match = re.search(r',(.+)', line)
            current_name = match.group(1).strip() if match else "Unknown"
        elif line and not line.startswith("#") and '.m3u8' in line:
            full_url = line if line.startswith("http") else base_url + line
            streams.append((current_name, full_url))
            current_name = ""
    return streams

def parse_txt(content: str) -> List[Tuple[str, str]]:
    streams = []
    for line in content.splitlines():
        if ',' in line:
            name, url = line.split(',', 1)
            if '.m3u8' in url:
                streams.append((name.strip(), url.strip()))
    return streams

def classify_channel(name: str) -> str:
    name = name.upper()
    if re.search(r'(CCTV|央視|中央)', name): return "cctv"
    if re.search(r'(凤凰|Phoenix)', name): return "phoenix"
    weishi_keywords = ['湖南卫视','江苏卫视','浙江卫视','东方卫视','安徽卫视','山东卫视','北京卫视','广东卫视']
    for kw in weishi_keywords:
        if kw in name: return "weishi"
    return "local"

def test_stream(url: str) -> bool:
    try:
        resp = requests.head(url, timeout=8, allow_redirects=True)
        return 200 <= resp.status_code < 400
    except:
        return False

def generate_txt_file(streams: List[Tuple[str, str]], filename: str):
    with open(filename, "w", encoding="utf-8") as f:
        for name, url in streams:
            f.write(f"{name},{url}\n")

def main():
    with open("subscriptions.txt") as f:
        subs = [line.strip() for line in f if line.strip()]

    all_streams = []
    for i, sub_url in enumerate(subs, 1):
        print(f"[{i}/{len(subs)}] Fetching: {sub_url}")
        content = fetch_content(sub_url)
        if "?json=true" in sub_url:
            parsed = parse_json(content)
        elif sub_url.endswith('.txt'):
            parsed = parse_txt(content)
        else:
            parsed = parse_m3u(content, sub_url)
        all_streams.extend(parsed)
        print(f"   → {len(parsed)} streams")

    print(f"\n总计: {len(all_streams)} streams")

    categories = {"cctv": [], "weishi": [], "phoenix": [], "local": []}
    for name, url in all_streams:
        cat = classify_channel(name)
        categories[cat].append((name, url))

    print("\n分类统计:")
    for cat, streams in categories.items():
        print(f"- {cat.upper()}: {len(streams)}")

    valid_categories = {}
    for category, streams in categories.items():
        if streams:
            test_name, test_url = streams[0]
            print(f"\n[{category.upper()}] 测试: {test_name}")
            if test_stream(test_url):
                valid_categories[category] = streams
                print(f"✓ 保留 {len(streams)} 行")

    all_valid = []
    for streams in valid_categories.values():
        all_valid.extend(streams)

    generate_txt_file(all_valid, "live_sources.txt")
    
    print(f"\n🎉 完成! 总行数: {len(all_valid)}")

if __name__ == "__main__":
    main()
