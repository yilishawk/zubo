import re
import requests
import time
import os

# 定义要提取的网页列表
urls = {
    "https://fofa.info/result?qbase64=InVkcHh5IiAmJiBjb3VudHJ5PSJDTiI%3D": "ip.txt",
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

all_ip_ports = set()  # 原始 IP:端口
all_ips = []          # 用于归属地查询的纯 IP

# 1️⃣ 抓网页，收集所有 IP:端口
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
                all_ips.append(ip)
                all_ip_ports.add(f"{ip}:{port}")
            else:
                ip = url_ip
                all_ips.append(ip)
                all_ip_ports.add(ip)
        print(f'{filename} 爬取完毕，共收集 {len(all_ip_ports)} 个 IP:端口')
    except Exception as e:
        print(f"爬取 {filename} 失败：{e}")
    time.sleep(3)

# 2️⃣ 单个查询 IP 信息
city_isp_dict = {}

for ip in all_ips:
    try:
        resp = requests.get(f"http://ip-api.com/json/{ip}?lang=zh-CN", timeout=10)
        info = resp.json()
        city = info.get("city", "未知")
        isp = info.get("isp", "其他")

        if "电信" in isp:
            isp_name = "电信"
        elif "联通" in isp:
            isp_name = "联通"
        elif "移动" in isp:
            isp_name = "移动"
        else:
            continue  # 不需要其他运营商

        filename = f"{city}{isp_name}.txt"
        if filename not in city_isp_dict:
            city_isp_dict[filename] = set()

        # 遍历 all_ip_ports，把对应 IP 的端口加进文件
        for ip_port in all_ip_ports:
            if ip_port.startswith(ip):
                city_isp_dict[filename].add(ip_port)

        time.sleep(0.5)  # 避免频繁请求
    except Exception as e:
        print(f"{ip} 查询失败：{e}")
        continue

# 3️⃣ 保存文件
for filename, ip_set in city_isp_dict.items():
    with open(filename, "w", encoding="utf-8") as f:
        for ip_port in sorted(ip_set):
            f.write(ip_port + "\n")
    print(f"{filename} 已生成，共 {len(ip_set)} 个 IP:端口")
