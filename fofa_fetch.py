import os
import requests
import json
import time
import socket
import subprocess

# ----------------------------
# 配置部分
# ----------------------------
# 城市列表，可以按需修改
CITIES = ["Beijing", "Hubei", "Guizhou", "Hunan", "Hebei"]

# FOFA 查询模板
QUERY_TEMPLATE = 'country="CN" && region="{city}"'

PAGE_SIZE = 100  # 每页抓取数量，可改

SAVE_DIR = "fofa_ip"  # 保存目录

# 获取 FOFA 邮箱和 API Key（环境变量）
FOFA_EMAIL = os.getenv("FOFA_EMAIL")
FOFA_KEY = os.getenv("FOFA_KEY")

if not FOFA_EMAIL or not FOFA_KEY:
    raise ValueError("请先在环境变量中设置 FOFA_EMAIL 和 FOFA_KEY")

# FOFA API URL
FOFA_API = "https://fofa.info/api/v1/search/all"

# ----------------------------
# 工具函数
# ----------------------------
def query_fofa(city):
    """抓取 FOFA 指定城市的 IP 数据"""
    query = QUERY_TEMPLATE.format(city=city)
    params = {
        "email": FOFA_EMAIL,
        "key": FOFA_KEY,
        "qbase64": requests.utils.quote(query.encode('utf-8')),
        "size": PAGE_SIZE
    }
    try:
        response = requests.get(FOFA_API, params=params, timeout=15)
        data = response.json()
        if data.get("error"):
            print(f"[{city}] FOFA API 错误: {data.get('errmsg')}")
            return []
        results = data.get("results", [])
        return results
    except Exception as e:
        print(f"[{city}] FOFA 请求失败: {e}")
        return []

def classify_ip(ip):
    """根据 IP 简单分类运营商（电信/联通/移动）"""
    # 这里用简单段判断，真实可改为 IP 库或在线接口
    if ip.startswith("1."):
        return "ChinaTelecom"
    elif ip.startswith("2."):
        return "ChinaUnicom"
    else:
        return "ChinaMobile"

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

# ----------------------------
# 主逻辑
# ----------------------------
ensure_dir(SAVE_DIR)
all_files = []

for city in CITIES:
    print(f"抓取城市: {city}")
    results = query_fofa(city)
    city_data = {"ChinaTelecom": set(), "ChinaUnicom": set(), "ChinaMobile": set()}

    for item in results:
        url = item[0]  # FOFA 返回的 URL
        # 提取 IP:Port
        try:
            ip_port = url.split("//")[-1]  # 去掉 http://
            if "/" in ip_port:
                ip_port = ip_port.split("/")[0]
            if ":" in ip_port:
                ip, port = ip_port.split(":")
            else:
                ip = ip_port
                port = "80"
            ip_port_clean = f"{ip}:{port}"
            isp = classify_ip(ip)
            city_data[isp].add(ip_port_clean)
        except Exception as e:
            continue

    # 按 ISP 保存文件，覆盖旧文件
    for isp, ipset in city_data.items():
        filename = os.path.join(SAVE_DIR, f"{city}_{isp}.txt")
        with open(filename, "w", encoding="utf-8") as f:
            for ip in sorted(ipset):
                f.write(ip + "\n")
        all_files.append(filename)
        print(f"保存文件: {filename}, 共 {len(ipset)} 条")

# ----------------------------
# Git 提交更新
# ----------------------------
try:
    subprocess.run(["git", "config", "--global", "user.email", "github-actions@github.com"], check=True)
    subprocess.run(["git", "config", "--global", "user.name", "github-actions"], check=True)
    subprocess.run(["git", "add"] + all_files, check=True)
    subprocess.run(["git", "commit", "-m", "Update FOFA IP files"], check=True)
    subprocess.run(["git", "push"], check=True)
    print("已提交更新到仓库")
except subprocess.CalledProcessError as e:
    print(f"Git 提交失败: {e}")
