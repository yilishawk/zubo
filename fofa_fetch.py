import re
import requests
import os
import time

# 定义要提取的网页列表和对应的保存文件名
urls = {
    "https://fofa.info/result?qbase64=InVkcHh5IiAmJiBjb3VudHJ5PSJDTiI%3D": "ip.txt",
}
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

all_ips = []

# 1️⃣ 抓网页，收集所有 IP:PORT
for url, filename in urls.items():
    try:
        print(f'正在爬取 {filename} .....')
        response = requests.get(url, headers=headers, timeout=15)
        page_content = response.text
        pattern = r'<a href="http://(.*?)" target="_blank">'
        urls_all = re.findall(pattern, page_content)
        for url_ip in urls_all:
            all_ips.append(url_ip)  # 保留 IP:PORT
        print(f'{filename} 爬取完毕，共收集 {len(all_ips)} 个 IP:PORT')
    except Exception as e:
        print(f"爬取 {filename} 失败：{e}")
    time.sleep(3)


# 2️⃣ 判断运营商函数（按 IP 段匹配，不用查归属地）
def get_isp(ip):
    # 电信
    if re.match(r"^(1(3[3-9]|47|53|7[37]|8[019])|349|36|37|39|42|43|45|49|58|59|60|61|100|101|102|103|104|105|106|107|108|109|110|111|112|113|114|115|116|117|118|119|120|121|122|123|124|125|126|127|175|176|177|178|180|181|182|183|184|185|186|187|188|189|199|223)\.", ip):
        return "电信"
    # 联通
    elif re.match(r"^(130|131|132|145|155|156|166|171|175|176|185|186|196|170)\.", ip):
        return "联通"
    # 移动
    elif re.match(r"^(134|135|136|137|138|139|147|150|151|152|157|158|159|182|183|184|187|188|195|198|199|178|170)\.", ip):
        return "移动"
    else:
        return "未知"


# 3️⃣ 按城市和运营商生成文件
city_isp_dict = {}

for ip_port in all_ips:
    if ':' in ip_port:
        ip, port = ip_port.split(':')
    else:
        ip = ip_port
        port = ''
    isp_name = get_isp(ip)
    if isp_name == "未知":
        continue  # 不保存未知运营商
    # 先获取城市信息
    city = "未知"  # 默认未知
    try:
        resp = requests.get(f"http://ip-api.com/json/{ip}?lang=zh-CN", timeout=10)
        result = resp.json()
        city = result.get("city", "未知")
    except Exception as e:
        print(f"{ip} 查询城市失败：{e}")
    filename = f"{city}{isp_name}.txt"
    if filename not in city_isp_dict:
        city_isp_dict[filename] = set()
    city_isp_dict[filename].add(ip_port)  # 保留端口

    time.sleep(0.5)  # 避免请求过快

# 4️⃣ 保存文件
for filename, ip_set in city_isp_dict.items():
    with open(filename, "w", encoding="utf-8") as f:
        for ip_port in sorted(ip_set):
            f.write(ip_port + "\n")
    print(f"{filename} 已生成，{len(ip_set)} 个 IP:PORT")
