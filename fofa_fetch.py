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

all_ips = []

# 1️⃣ 抓网页，收集所有 IP:port
for url, filename in urls.items():
    try:
        print(f'正在爬取 {filename} .....')
        response = requests.get(url, headers=headers, timeout=15)
        page_content = response.text
        pattern = r'<a href="http://(.*?)" target="_blank">'
        urls_all = re.findall(pattern, page_content)
        for url_ip in urls_all:
            all_ips.append(url_ip.strip())
        print(f'{filename} 爬取完毕，共收集 {len(all_ips)} 个 IP:port')
    except Exception as e:
        print(f"爬取 {filename} 失败：{e}")
    time.sleep(3)

city_isp_dict = {}

# 2️⃣ 单 IP 查询归属地
for ip_port in all_ips:
    if ':' in ip_port:
        ip, port = ip_port.split(':')
    else:
        ip, port = ip_port, ''
    try:
        resp = requests.get(f"http://ip-api.com/json/{ip}?lang=zh-CN", timeout=10)
        data = resp.json()
        city = data.get("city", "未知")
        isp = data.get("isp", "其他")

        if "电信" in isp:
            isp_name = "电信"
        elif "联通" in isp:
            isp_name = "联通"
        elif "移动" in isp:
            isp_name = "移动"
        else:
            isp_name = "其他"

        filename = f"{city}{isp_name}.txt"
        if filename not in city_isp_dict:
            city_isp_dict[filename] = set()
        city_isp_dict[filename].add(f"{ip}:{port}")

        print(f"{ip}:{port} -> {city} {isp_name}")

    except Exception as e:
        print(f"{ip_port} 查询失败：{e}")
    time.sleep(1)  # 避免封 IP

# 3️⃣ 保存文件
for filename, ip_set in city_isp_dict.items():
    with open(filename, "w", encoding="utf-8") as f:
        for ip_port in sorted(ip_set):
            f.write(ip_port + "\n")
    print(f"{filename} 已生成，共 {len(ip_set)} 个 IP")
