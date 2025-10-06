import os
import requests
import json
import ipaddress
import time

# FOFA API 配置，通过环境变量
FOFA_EMAIL = os.getenv("FOFA_EMAIL")
FOFA_KEY = os.getenv("FOFA_KEY")

# FOFA 查询
# 例：抓取所有中国IP
QUERY = 'country="CN"'
PAGE_SIZE = 100

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# 查询 FOFA API
def fofa_search(email, key, query, page=1, size=100):
    url = f"https://fofa.info/api/v1/search/all?email={email}&key={key}&qbase64={query}&page={page}&size={size}"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        return resp.json()
    else:
        print("FOFA API 请求失败:", resp.text)
        return None

# 示例 IP 归属地 + 运营商判断（可换专业库）
def classify_ip(ip):
    # 这里只是演示
    # 实际可调用第三方库如 `ipwhois`、`geoip2` 或在线接口
    # 返回 (城市, 运营商)
    if ip.startswith("1."):
        return "Beijing", "电信"
    elif ip.startswith("2."):
        return "Shanghai", "联通"
    else:
        return "Guangdong", "移动"

# 保存文件
def save_ip(city, isp, ip_list):
    filename = f"{city}{isp}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        for ip in sorted(set(ip_list)):
            f.write(ip + "\n")
    print(f"{filename} 已保存 {len(ip_list)} 条 IP")

# 主流程
def main():
    all_ips = {}
    # FOFA API 返回结果示例，实际需要解析 response['results']
    # 这里我们做模拟
    # resp = fofa_search(FOFA_EMAIL, FOFA_KEY, QUERY)
    # 假设拿到以下 IP 列表：
    ip_data = ["1.1.1.1:80", "1.2.3.4:8080", "2.3.4.5:443", "3.4.5.6:80"]
    for ip_port in ip_data:
        ip = ip_port.split(":")[0]
        city, isp = classify_ip(ip)
        key = (city, isp)
        if key not in all_ips:
            all_ips[key] = []
        all_ips[key].append(ip_port)
        time.sleep(0.1)  # 避免过快请求
    # 保存文件
    for (city, isp), ip_list in all_ips.items():
        save_ip(city, isp, ip_list)

if __name__ == "__main__":
    main()
