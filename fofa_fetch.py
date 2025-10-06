import re
import requests
import time

# -------------------------------
urls = {
    "https://fofa.info/result?qbase64=InVkcHh5IiAmJiBjb3VudHJ5PSJDTiI%3D": "ip.txt",
}
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# -------------------------------
def get_isp(ip):
    # 电信
    if re.match(r"^((1[0-9]|2[0-3])\d{2}|42|43|58|59|60|61|110|111|112|113|114|115|116|117|118|119|120|121|122|123|124|125|126|127|175|180|182|183|184|185|186|187|188|189|223)\.", ip):
        return "电信"
    # 联通
    elif re.match(r"^(42|43|58|59|60|61|110|111|112|113|114|115|116|117|118|119|120|121|122|123|124|125|126|127|175|180|182|183|184|185|186|187|188|189|223)\.", ip):
        return "联通"
    # 移动
    elif re.match(r"^(223|36|37|38|39|100|101|102|103|104|105|106|107|108|109|134|135|136|137|138|139|150|151|152|157|158|159|170|178|182|183|184|187|188|189)\.", ip):
        return "移动"
    else:
        return "未知"

# -------------------------------
all_ips = set()

for url, filename in urls.items():
    try:
        print(f'正在爬取 {filename} .....')
        response = requests.get(url, headers=headers, timeout=15)
        page_content = response.text
        pattern = r'<a href="http://(.*?)" target="_blank">'
        urls_all = re.findall(pattern, page_content)
        for url_ip in urls_all:
            all_ips.add(url_ip.strip())
        print(f'{filename} 爬取完毕，共收集 {len(all_ips)} 个 IP')
    except Exception as e:
        print(f"爬取 {filename} 失败：{e}")
    time.sleep(3)

# -------------------------------
province_isp_dict = {}

for ip_port in all_ips:
    try:
        if ':' in ip_port:
            ip, port = ip_port.split(':')
        else:
            ip, port = ip_port, ''

        # 获取省份信息
        resp = requests.get(f"http://ip-api.com/json/{ip}?lang=zh-CN", timeout=10)
        data = resp.json()
        province = data.get("regionName", "未知")  # 按省份分类
        isp_name = get_isp(ip)
        if isp_name == "未知":
            continue

        filename = f"{province}{isp_name}.txt"  # 文件名按省份+运营商
        if filename not in province_isp_dict:
            province_isp_dict[filename] = set()
        province_isp_dict[filename].add(ip_port)  # 保留 IP:端口格式

        time.sleep(0.5)  # 防止请求过快
    except Exception as e:
        print(f"{ip_port} 查询失败：{e}")
        continue

# -------------------------------
for filename, ip_set in province_isp_dict.items():
    with open(filename, "w", encoding="utf-8") as f:  # 覆盖写入
        for ip_port in sorted(ip_set):
            f.write(ip_port + "\n")
    print(f"{filename} 已生成，{len(ip_set)} 个 IP")