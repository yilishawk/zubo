import base64
import requests
import json
import re
import os
from concurrent.futures import ThreadPoolExecutor
from ipaddress import ip_address

EMAIL = os.getenv("FOFA_EMAIL")
KEY = os.getenv("FOFA_KEY")

if not EMAIL or not KEY:
    print("❌ 未检测到 FOFA_EMAIL 或 FOFA_KEY 环境变量，请在 GitHub Secrets 设置中添加。")
    exit(1)

QUERY = 'port="80"'
QBASE64 = base64.b64encode(QUERY.encode()).decode()

def get_fofa_data(page=1):
    url = f"https://fofa.info/api/v1/search/all?email={EMAIL}&key={KEY}&qbase64={QBASE64}&page={page}"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        return data.get("results", [])
    except Exception as e:
        print("请求错误：", e)
        return []

def extract_ip_port(urls):
    result = set()
    for u in urls:
        match = re.match(r"https?://([\w\.\-\[\]:]+)", u)
        if match:
            host = match.group(1)
            if ":" not in host:
                continue
            ip, port = host.split(":", 1)
            try:
                ip_address(ip.strip("[]"))
                result.add(f"{ip}:{port}")
            except ValueError:
                continue
    return result

def get_ip_info(ip):
    try:
        url = f"http://ip-api.com/json/{ip}?lang=zh-CN"
        res = requests.get(url, timeout=5)
        data = res.json()
        city = data.get("city", "未知城市")
        isp = data.get("isp", "未知运营商")

        if "电信" in isp:
            isp = "电信"
        elif "联通" in isp:
            isp = "联通"
        elif "移动" in isp:
            isp = "移动"
        else:
            isp = "其他"
        return city, isp
    except:
        return "未知城市", "其他"

def save_to_file(city, isp, data):
    if not city:
        city = "未知城市"
    filename = f"{city}{isp}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(data)))
    print(f"✅ 已保存：{filename}（{len(data)} 条）")

all_ips = set()
for page in range(1, 6):  # 获取前5页
    print(f"正在获取第 {page} 页...")
    results = get_fofa_data(page)
    if not results:
        break
    all_ips |= extract_ip_port([r[0] for r in results])

print(f"共提取 {len(all_ips)} 个 IP:端口")

ip_groups = {}
with ThreadPoolExecutor(max_workers=10) as executor:
    for ipport in all_ips:
        ip = ipport.split(":")[0]
        city, isp = get_ip_info(ip)
        key = f"{city}-{isp}"
        ip_groups.setdefault(key, set()).add(ipport)

for key, data in ip_groups.items():
    city, isp = key.split("-")
    save_to_file(city, isp, data)
