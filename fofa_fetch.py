import re
import requests
import os
import time

urls = {
    "https://fofa.info/result?qbase64=InVkcHh5IiAmJiBjb3VudHJ5PSJDTiI%3D": "ip.txt",
}
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

all_ips = set()

# 1️⃣ 抓网页，收集所有 IP
for url, filename in urls.items():
    try:
        print(f'正在爬取 {filename} .....')
        response = requests.get(url, headers=headers, timeout=15)
        page_content = response.text
        pattern = r'<a href="http://(.*?)" target="_blank">'
        urls_all = re.findall(pattern, page_content)
        for url_ip in urls_all:
            if ':' in url_ip:
                ip, port = url_ip.split(':')
            else:
                ip = url_ip
            all_ips.add(ip)
        print(f'{filename} 爬取完毕，共收集 {len(all_ips)} 个 IP')
    except Exception as e:
        print(f"爬取 {filename} 失败：{e}")
    time.sleep(3)

# 2️⃣ 批量查询 IP 信息
def chunk_list(lst, n):
    """将 lst 分割成每 n 个元素一组"""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

city_isp_dict = {}

for batch in chunk_list(list(all_ips), 100):
    try:
        data = [{"query": ip} for ip in batch]
        resp = requests.post("http://ip-api.com/batch?lang=zh-CN", json=data, timeout=15)
        results = resp.json()
        for item in results:
            ip = item.get("query")
            city = item.get("city", "未知")
            isp = item.get("isp", "其他")
            if "电信" in isp:
                isp_name = "电信"
            elif "联通" in isp:
                isp_name = "联通"
            elif "移动" in isp:
                isp_name = "移动"
            else:
                continue  # 其他不保存
            filename = f"{city}{isp_name}.txt"
            if filename not in city_isp_dict:
                city_isp_dict[filename] = set()
            city_isp_dict[filename].add(ip)
        time.sleep(1)
    except Exception as e:
        print(f"批量查询失败：{e}")
        continue

# 3️⃣ 保存文件
for filename, ip_set in city_isp_dict.items():
    with open(filename, "w", encoding="utf-8") as f:
        for ip in sorted(ip_set):
            f.write(ip + "\n")
    print(f"{filename} 已生成，{len(ip_set)} 个 IP")
