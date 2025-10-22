#!/usr/bin/env python3
import requests
import json
import re
from typing import List, Tuple
import urllib.parse

def fetch_content(url: str) -> str:
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.text
    except:
        return ""

def parse_m3u(content: str, base_url: str = "") -> List[Tuple[str, str]]:
    """解析标准M3U格式"""
    streams = []
    lines = content.splitlines()
    current_name = ""
    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF:"):
            match = re.search(r',(.+)', line)
            current_name = match.group(1).strip() if match else "Unknown"
        elif line and not line.startswith("#"):
            # 支持 .m3u8 和 PHP链接
            if (line.endswith(".m3u8") or ".m3u8" in line or "iptv2A.php" in line):
                full_url = line if line.startswith("http") else base_url + line
                streams.append((current_name, full_url))
                current_name = ""
    return streams

def parse_txt_fytv(content: str) -> List[Tuple[str, str]]:
    """专门解析 FYTV.txt 格式"""
    streams = []
    lines = content.splitlines()
    for line in lines:
        line = line.strip()
        if "," in line and "iptv2A.php" in line:
            parts = line.split(",", 1)
            if len(parts) >= 2:
                name = parts[0].strip()
                url = parts[1].strip()
                streams.append((name, url))
    return streams

def parse_txt_simple(content: str) -> List[Tuple[str, str]]:
    """简单TXT解析"""
    streams = []
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("http"):
            streams.append((line, line))
    return streams

def parse_json(content: str) -> List[Tuple[str, str]]:
    """解析JSON"""
    try:
        data = json.loads(content)
        streams = []
        if isinstance(data, list):
            for item in data:
                name = item.get('name', 'Unknown')
                url = item.get('url', '')
                if url:
                    streams.append((name, url))
        return streams
    except:
        return []

def classify_channel(name: str) -> str:
    name = name.upper()
    if re.search(r'(CCTV|央視|中央)', name): return "cctv"
    if re.search(r'(凤凰|Phoenix)', name): return "phoenix"
    weishi_keywords = ['湖南卫视','江苏卫视','浙江卫视','东方卫视','安徽卫视','山东卫视','北京卫视','广东卫视','河南卫视','湖北卫视']
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
        
        parsed = []
        if "4666888.xyz/FYTV.txt" in sub_url:
            parsed = parse_txt_fytv(content)
            print(f"   → FYTV: {len(parsed)} streams")
        elif "?json=true" in sub_url:
            parsed = parse_json(content)
            print(f"   → JSON: {len(parsed)} streams")
        elif sub_url.endswith('.txt'):
            parsed = parse_txt_simple(content)
            print(f"   → TXT: {len(parsed)} streams")
        else:
            parsed = parse_m3u(content, sub_url)
            print(f"   → M3U: {len(parsed)} streams")
        
        # 显示前3个
        for j, (name, url) in enumerate(parsed[:3]):
            print(f"      {j+1}. {name} -> {url[:60]}...")
        
        all_streams.extend(parsed)

    print(f"\n总计: {len(all_streams)} streams")

    # 分类
    categories = {"cctv": [], "weishi": [], "phoenix": [], "local": []}
    for name, url in all_streams:
        cat = classify_channel(name)
        categories[cat].append((name, url))

    print("\n分类统计:")
    for cat, streams in categories.items():
        print(f"- {cat.upper()}: {len(streams)}")

    # 测试 (每个分类1次)
    valid_categories = {}
    for category, streams in categories.items():
        if streams:
            test_name, test_url = streams[0]
            print(f"\n[{category.upper()}] 测试: {test_name}")
            if test_stream(test_url):
                valid_categories[category] = streams
                print(f"✓ 保留 {len(streams)} 行")

    # 合并
    all_valid = []
    for streams in valid_categories.values():
        all_valid.extend(streams)

    generate_txt_file(all_valid, "live_sources.txt")
    
    print(f"\n🎉 完成! 总行数: {len(all_valid)}")

if __name__ == "__main__":
    main()
