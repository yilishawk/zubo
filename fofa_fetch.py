import os
import re
import requests
import time
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

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
OUTPUT_FILE = "IPTV.txt"

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
    os.makedirs(IP_DIR, exist_ok=True)
    count = get_run_count() + 1
    if count >= 73:
        for file in os.listdir(IP_DIR):
            if file.endswith(".txt"):
                os.remove(os.path.join(IP_DIR, file))
        save_run_count(1)
        return "w", 1
    else:
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
# 频道映射与分类
CHANNEL_CATEGORIES = {
    "央视频道": ["CCTV1", "CCTV2"],
    "卫视频道": ["湖南卫视", "浙江卫视"],
    "数字频道": ["CHC动作电影", "CHC家庭影院", "CHC影迷电影"]
}

CHANNEL_MAPPING = {
    "CCTV1": ["CCTV-1", "CCTV-1 HD", "CCTV1 HD", "CCTV-1综合", "CCTV1 4M1080", "CCTV1 5M1080HEVC"],
    "CCTV2": ["CCTV-2", "CCTV-2 HD", "CCTV2 HD", "CCTV-2财经"],
    "湖南卫视": ["湖南", "湖南HD", "湖南卫视高清"],
    "浙江卫视": ["浙江", "浙江HD", "浙江卫视高清"],
    "CHC动作电影": ["CHC动作", "CHC动作HD"],
    "CHC家庭影院": ["CHC家庭", "CHC家庭HD"],
    "CHC影迷电影": ["CHC影迷", "CHC影迷HD"]
}

def map_channel(name):
    for std_name, aliases in CHANNEL_MAPPING.items():
        for alias in aliases:
            if alias.lower() in name.lower():
                return std_name
    return name.strip()

# ===============================
# 使用 ffprobe 检测可播放性
def check_stream_playable(url, timeout=5):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-timeout", str(timeout*1000000), "-i", url],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout+2
        )
        return b"Stream #" in result.stderr
    except Exception:
        return False

# ===============================
# 第一阶段：爬取 FOFA IP
all_ips = set()
for url, filename in FOFA_URLS.items():
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        pattern = r'<a href="http://(.*?)" target="_blank">'
        all_ips.update([u.strip() for u in re.findall(pattern, resp.text)])
    except Exception:
        pass

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
        province_isp_dict.setdefault(fname, set()).add(ip_port)
        time.sleep(0.5)
    except Exception:
        continue

write_mode, run_count = check_and_clear_files_by_run_count()
for filename, ip_set in province_isp_dict.items():
    save_path = os.path.join(IP_DIR, filename)
    with open(save_path, write_mode, encoding="utf-8") as f:
        for ip_port in sorted(ip_set):
            f.write(ip_port + "\n")

# ===============================
# 第二阶段触发条件
trigger_points = [12, 24, 36, 48, 60, 72]

if run_count in trigger_points:
    combined_lines = []

    for ip_file in os.listdir(IP_DIR):
        if not ip_file.endswith(".txt"):
            continue
        ip_path = os.path.join(IP_DIR, ip_file)
        rtp_path = os.path.join(RTP_DIR, ip_file)
        if not os.path.exists(rtp_path):
            continue
        province_operator = ip_file.replace(".txt", "")
        with open(ip_path, "r", encoding="utf-8") as f_ip, open(rtp_path, "r", encoding="utf-8") as f_rtp:
            ip_lines = [line.strip() for line in f_ip if line.strip()]
            rtp_lines = [line.strip() for line in f_rtp if line.strip()]

        if not ip_lines or not rtp_lines:
            continue

        def process_ip(ip_port):
            channels = []
            for rtp_line in rtp_lines:
                if "," in rtp_line:
                    ch_name, rtp_url = rtp_line.split(",", 1)
                    channels.append((ch_name, rtp_url))

            # CCTV1 检测
            cctv1_urls = [f"http://{ip_port}/rtp/{u.split('rtp://')[1]}" for ch, u in channels if "CCTV1" in ch]
            if not any(check_stream_playable(u) for u in cctv1_urls):
                return []

            # CCTV1 可播，保留全部频道
            return [(ch, f"http://{ip_port}/rtp/{u.split('rtp://')[1]}") for ch, u in channels]

        with ThreadPoolExecutor(max_workers=10) as executor:
            results = executor.map(process_ip, ip_lines)
            for res in results:
                combined_lines.extend(res)

    # 分类、排序
    category_map = {cat: [] for cat in CHANNEL_CATEGORIES.keys()}
    for ch_name, url in combined_lines:
        mapped = map_channel(ch_name)
        for cat, keywords in CHANNEL_CATEGORIES.items():
            if mapped in keywords:
                category_map[cat].append(f"{mapped},{url}")
                break

    # 写入 IPTV.txt
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for cat, lines in category_map.items():
            f.write(f"{cat},#genre#\n")
            for line in sorted(set(lines)):
                f.write(f"{line}\n")
            f.write("\n")

    # 推送
    os.system('git config --global user.email "github-actions@users.noreply.github.com"')
    os.system('git config --global user.name "github-actions"')
    os.system("git add IPTV.txt")
    os.system(f'git commit -m "自动更新 IPTV.txt（第 {run_count} 次）" || echo "⚠️ 无需提交"')
    os.system("git push")