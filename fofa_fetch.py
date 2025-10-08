import os
import re
import requests
import time
from datetime import datetime
import concurrent.futures

# ===============================
# 配置
FOFA_URLS = {
    "https://fofa.info/result?qbase64=InVkcHh5IiAmJiBjb3VudHJ5PSJDTiI%3D": "ip.txt",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

COUNTER_FILE = "计数.txt"
IP_DIR = "ip"
RTP_DIR = "rtp"
ZUBO_FILE = "zubo.txt"

# ===============================
# 计数管理
def get_run_count():
    if os.path.exists(COUNTER_FILE):
        try:
            with open(COUNTER_FILE, "r", encoding="utf-8") as f:
                return int(f.read().strip())
        except Exception:
            return 0
    return 0

def save_run_count(count):
    with open(COUNTER_FILE, "w", encoding="utf-8") as f:
        f.write(str(count))

def check_and_clear_files_by_run_count():
    """
    每运行19次清空 IP_DIR 下所有 txt 文件。
    前18次追加，第19次清空覆盖。
    返回写入模式 w 或 a
    """
    os.makedirs(IP_DIR, exist_ok=True)
    count = get_run_count() + 1
    if count >= 19:
        print(f"🧹 第 {count} 次运行，清空 {IP_DIR} 下所有 .txt 文件...")
        for file in os.listdir(IP_DIR):
            if file.endswith(".txt"):
                os.remove(os.path.join(IP_DIR, file))
                print(f"已删除：{file}")
        save_run_count(1)  # 清空后计数从1开始
        return "w", 1
    else:
        print(f"⏰ 当前第 {count} 次运行，本次执行为追加模式")
        save_run_count(count)
        return "a", count

# ===============================
# IP运营商判断
def get_isp(ip):
    if re.match(r"^(1[0-9]{2}|2[0-3]{2}|42|43|58|59|60|61|110|111|112|113|114|115|116|117|118|119|120|121|122|123|124|125|126|127|175|180|182|183|184|185|186|187|188|189|223)\.", ip):
        return "电信"
    elif re.match(r"^(42|43|58|59|60|61|110|111|112|113|114|115|116|117|118|119|120|121|122|123|124|125|126|127|175|180|182|183|184|185|186|187|188|189|223)\.", ip):
        return "联通"
    elif re.match(r"^(223|36|37|38|39|100|101|102|103|104|105|106|107|108|109|134|135|136|137|138|139|150|151|152|157|158|159|170|178|182|183|184|187|188|189)\.", ip):
        return "移动"
    return "未知"

# ===============================
# 第一阶段：爬取 FOFA IP 并分类写入 ip/
all_ips = set()
for url, filename in FOFA_URLS.items():
    try:
        print(f"正在爬取 {filename} ...")
        resp = requests.get(url, headers=HEADERS, timeout=15)
        page_content = resp.text
        pattern = r'<a href="http://(.*?)" target="_blank">'
        urls_all = re.findall(pattern, page_content)
        for u in urls_all:
            all_ips.add(u.strip())
        print(f"{filename} 爬取完成，共 {len(all_ips)} 个 IP")
    except Exception as e:
        print(f"爬取 {filename} 失败：{e}")
    time.sleep(3)

province_isp_dict = {}
for ip_port in all_ips:
    try:
        ip = ip_port.split(':')[0]
        resp = requests.get(f"http://ip-api.com/json/{ip}?lang=zh-CN", timeout=10)
        data = resp.json()
        province = data.get("regionName", "未知")
        isp_name = get_isp(ip)
        if isp_name == "未知":
            continue
        fname = f"{province}{isp_name}.txt"
        if fname not in province_isp_dict:
            province_isp_dict[fname] = set()
        province_isp_dict[fname].add(ip_port)
        time.sleep(0.5)
    except Exception as e:
        print(f"{ip_port} 查询失败：{e}")
        continue

write_mode, run_count = check_and_clear_files_by_run_count()

for filename, ip_set in province_isp_dict.items():
    save_path = os.path.join(IP_DIR, filename)
    with open(save_path, write_mode, encoding="utf-8") as f:
        for ip_port in sorted(ip_set):
            f.write(ip_port + "\n")
    print(f"{save_path} 已{'覆盖' if write_mode=='w' else '追加'}写入 {len(ip_set)} 个 IP")

print(f"✅ 第一阶段完成，本次运行轮次：{run_count}")

# ===============================
# ===== 第二阶段：触发条件（计数.txt 内容为 18）=====
if counter == 18:
    print("🔔 第二阶段触发：生成 zubo.txt")

    ip_dir = "ip"
    rtp_dir = "rtp"
    all_results = []

    # 检查 ip/ 与 rtp/ 目录是否存在
    if not os.path.exists(ip_dir) or not os.path.exists(rtp_dir):
        print("❌ 缺少 ip/ 或 rtp/ 文件夹，终止执行。")
        exit(0)

    # 遍历 ip 目录下所有 .txt 文件
    for ip_file in os.listdir(ip_dir):
        if not ip_file.endswith(".txt"):
            continue

        ip_path = os.path.join(ip_dir, ip_file)
        rtp_path = os.path.join(rtp_dir, ip_file)

        # 确保 rtp 下有对应文件
        if not os.path.exists(rtp_path):
            print(f"⚠️ 跳过 {ip_file}，rtp 文件不存在。")
            continue

        with open(ip_path, "r", encoding="utf-8") as f:
            ip_lines = [line.strip() for line in f if line.strip()]

        with open(rtp_path, "r", encoding="utf-8") as f:
            rtp_lines = [line.strip() for line in f if line.strip()]

        if not ip_lines or not rtp_lines:
            print(f"⚠️ 跳过 {ip_file}，文件内容为空。")
            continue

        # 多线程检测第一行
        first_rtp = rtp_lines[0]
        valid_ips = []
        print(f"🔍 检测 {ip_file} 中的可用 IP...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            future_to_ip = {
                executor.submit(check_stream_resolution, ip, first_rtp): ip for ip in ip_lines
            }
            for future in concurrent.futures.as_completed(future_to_ip):
                ip = future_to_ip[future]
                if future.result():
                    valid_ips.append(ip)

        if not valid_ips:
            print(f"❌ {ip_file} 无可用 IP，跳过。")
            continue

        # 对每个有效 IP 合并所有频道
        for ip_port in valid_ips:
            for rtp_line in rtp_lines:
                try:
                    name, rtp_url = rtp_line.split(",", 1)
                    # 兼容多种 rtp 格式
                    rtp_url = rtp_url.replace("rtp//:", "").replace("rtp://", "")
                    merged = f"{name},http://{ip_port}/rtp/{rtp_url}"
                    all_results.append(merged)
                except Exception as e:
                    print(f"⚠️ 格式错误（{ip_file}）: {rtp_line}")

    # ✅ 全局去重逻辑（核心改动）
    print("🧹 正在对所有 URL 进行去重处理...")
    unique_lines = []
    seen = set()
    for line in all_results:
        if line not in seen:
            seen.add(line)
            unique_lines.append(line)

    # 保存到 zubo.txt
    with open("zubo.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(unique_lines))

    print(f"✅ 第二阶段完成，共生成 {len(unique_lines)} 条唯一可用直播源。")