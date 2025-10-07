import os
import re
import requests
import time
from datetime import datetime

# ===============================
# 配置
IP_DIR = "ip"
RTP_DIR = "rtp"
COUNTER_FILE = "计数.txt"
ZUBO_FILE = "zubo.txt"

# 要爬取的 URL
urls = {
    "https://fofa.info/result?qbase64=InVkcHh5IiAmJiBjb3VudHJ5PSJDTiI%3D": "ip.txt",
}

# 请求头
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

# ===============================
# 计数管理
def get_run_count():
    if os.path.exists(COUNTER_FILE):
        try:
            with open(COUNTER_FILE, "r") as f:
                return int(f.read().strip())
        except:
            return 0
    return 0

def save_run_count(count):
    with open(COUNTER_FILE, "w") as f:
        f.write(str(count))

# ===============================
# IP 运营商判断
def get_isp(ip):
    if re.match(r"^(1[0-9]{2}|2[0-3]{2}|42|43|58|59|60|61|110|111|112|113|114|115|116|117|118|119|120|121|122|123|124|125|126|127|175|180|182|183|184|185|186|187|188|189|223)\.", ip):
        return "电信"
    elif re.match(r"^(42|43|58|59|60|61|110|111|112|113|114|115|116|117|118|119|120|121|122|123|124|125|126|127|175|180|182|183|184|185|186|187|188|189|223)\.", ip):
        return "联通"
    elif re.match(r"^(223|36|37|38|39|100|101|102|103|104|105|106|107|108|109|134|135|136|137|138|139|150|151|152|157|158|159|170|178|182|183|184|187|188|189)\.", ip):
        return "移动"
    else:
        return "未知"

# ===============================
# 判断写入模式，每19次清空 ip 文件夹
def check_and_clear_files_by_run_count():
    os.makedirs(IP_DIR, exist_ok=True)
    count = get_run_count() + 1

    if count >= 19:
        print(f"🧹 第 {count} 次运行，清空 {IP_DIR} 下所有 .txt 文件...")
        for file in os.listdir(IP_DIR):
            if file.endswith(".txt"):
                os.remove(os.path.join(IP_DIR, file))
                print(f"已删除：{file}")
        save_run_count(1)  # 清空后计数从1开始
        print("✅ 清空完成，本次执行为【覆盖写入模式】")
        return "w", 1
    else:
        print(f"⏰ 第 {count} 次运行，本次执行为【追加写入模式】")
        save_run_count(count)
        return "a", count

# ===============================
# IPTV 源检测函数
def detect_resolution(url, timeout=8):
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code != 200:
            return False, None
        content = resp.text
        if "#EXTM3U" not in content:
            return False, None
        match = re.search(r"RESOLUTION=(\d+x\d+)", content)
        if match:
            return True, match.group(1)
        elif "#EXTINF" in content:
            return True, "unknown"
        return False, None
    except:
        return False, None

# ===============================
# 第一阶段：爬取 IP 并分类
all_ips = set()
for url, filename in urls.items():
    try:
        print(f"正在爬取 {filename} .....")
        resp = requests.get(url, headers=headers, timeout=15)
        page_content = resp.text
        pattern = r'<a href="http://(.*?)" target="_blank">'
        for url_ip in re.findall(pattern, page_content):
            all_ips.add(url_ip.strip())
        print(f"{filename} 爬取完毕，共收集 {len(all_ips)} 个 IP")
    except Exception as e:
        print(f"爬取 {filename} 失败：{e}")
    time.sleep(2)

province_isp_dict = {}
for ip_port in all_ips:
    try:
        if ':' in ip_port:
            ip, port = ip_port.split(':')
        else:
            ip, port = ip_port, ''
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
    except:
        continue

write_mode, run_count = check_and_clear_files_by_run_count()

for filename, ip_set in province_isp_dict.items():
    save_path = os.path.join(IP_DIR, filename)
    with open(save_path, write_mode, encoding="utf-8") as f:
        for ip_port in sorted(ip_set):
            f.write(ip_port + "\n")
    print(f"{save_path} 已{'覆盖' if write_mode=='w' else '追加'}写入 {len(ip_set)} 个 IP")

print(f"🎯 第一阶段完成，本次运行轮次：{run_count}")

# ===============================
# 第二阶段：计数=18时触发
if run_count == 18:
    print("🚀 第二阶段开始，合并 ip/ 与 rtp/ 内容并检测直播流...")
    merged_lines = []

    for ip_file in os.listdir(IP_DIR):
        if not ip_file.endswith(".txt"):
            continue
        ip_path = os.path.join(IP_DIR, ip_file)
        rtp_path = os.path.join(RTP_DIR, ip_file)
        if not os.path.exists(rtp_path):
            continue

        with open(ip_path, "r", encoding="utf-8") as f:
            ip_lines = [line.strip() for line in f if line.strip()]
        with open(rtp_path, "r", encoding="utf-8") as f:
            rtp_lines = [line.strip() for line in f if line.strip()]

        if not ip_lines or not rtp_lines:
            continue

        first_rtp = rtp_lines[0]
        try:
            channel_name, rtp_url = first_rtp.split(",", 1)
        except:
            continue

        # 检测 IP 是否可用（仅检测第一行直播流）
        temp_merged = []
        for ip_port in ip_lines:
            new_url = f"{channel_name},http://{ip_port}/rtp/{rtp_url}"
            ok, _ = detect_resolution(f"http://{ip_port}/rtp/{rtp_url.split('rtp//:')[-1]}")
            if ok:
                temp_merged.append(new_url)
        if not temp_merged:
            continue

        # 剩余频道不检测，直接合并
        for ip_port in ip_lines:
            for line in rtp_lines[1:]:
                try:
                    ch_name, rtp_url = line.split(",", 1)
                    for merged_ip in temp_merged:
                        ip_only = merged_ip.split(",")[1].split("/rtp/")[0].replace("http://", "")
                        merged_lines.append(f"{ch_name},http://{ip_only}/rtp/{rtp_url}")
                except:
                    continue
        merged_lines.extend(temp_merged)

    # 保存到根目录 zubo.txt（覆盖写入）
    if merged_lines:
        with open(ZUBO_FILE, "w", encoding="utf-8") as f:
            for line in merged_lines:
                f.write(line + "\n")
        print(f"✅ 第二阶段完成，已生成 {ZUBO_FILE}")
    else:
        print("⚠️ 第二阶段没有生成有效内容")
else:
    print("⏭ 第二阶段未触发，计数不为18")
