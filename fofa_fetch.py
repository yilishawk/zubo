import os
import re
import requests
import time
import concurrent.futures
import subprocess

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
IPTV_FILE = "IPTV.txt"

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
    print(f"{save_path} 已{'覆盖' if write_mode=='w' else '追加'}写入 {len(ip_set)} 个 IP")

print(f"✅ 第一阶段完成，本次运行轮次：{run_count}")

# ===============================
# 第二阶段触发条件
trigger_points = [12, 24, 36, 48, 60, 72]

# ===============================
# 第二阶段：生成 zubo.txt（不推送）
if run_count in trigger_points:
    print(f"🔔 第二阶段触发：生成 zubo.txt（第 {run_count} 次）")
    combined_lines = []

    for ip_file in os.listdir(IP_DIR):
        if not ip_file.endswith(".txt"):
            continue
        ip_path = os.path.join(IP_DIR, ip_file)
        rtp_path = os.path.join(RTP_DIR, ip_file)
        if not os.path.exists(rtp_path):
            continue

        province_operator = ip_file.replace(".txt", "")
        with open(ip_path, "r", encoding="utf-8") as f_ip, \
             open(rtp_path, "r", encoding="utf-8") as f_rtp:
            ip_lines = [line.strip() for line in f_ip if line.strip()]
            rtp_lines = [line.strip() for line in f_rtp if line.strip()]

        if not ip_lines or not rtp_lines:
            continue

        for i, ip_port in enumerate(ip_lines, start=1):
            suffix = f"${province_operator}{i}"
            for rtp_line in rtp_lines:
                ch_name, rtp_url_rest = rtp_line.split(",", 1)
                combined_lines.append(f"{ch_name},http://{ip_port}/rtp/{rtp_url_rest.split('rtp://')[1]}{suffix}")

    with open(ZUBO_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(combined_lines))

    print(f"🎯 第二阶段完成，已生成 {len(combined_lines)} 条 URL")

    # ===============================
    # 第三阶段：检测 zubo.txt 并生成 IPTV.txt
    print("🔍 第三阶段开始：检测并生成 IPTV.txt ...")

    def check_url_playable(url):
        try:
            cmd = ["ffprobe", "-v", "error", "-timeout", "3000000", "-i", url]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
            return result.returncode == 0
        except Exception:
            return False

    # 按 IP 分组
    ip_groups = {}
    for line in combined_lines:
        ch, url = line.split(",", 1)
        ip = re.search(r"http://(.*?)/", url).group(1)
        ip_groups.setdefault(ip, []).append((ch, url))

    valid_lines = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for ip, lines in ip_groups.items():
            cctv1_urls = [u for ch, u in lines if "CCTV1" in ch]
            ok = any(executor.submit(check_url_playable, u).result() for u in cctv1_urls)
            if ok:
                valid_lines.extend(lines)

    # 频道映射
    def map_channel(name):
        for std, aliases in CHANNEL_MAPPING.items():
            if name.strip() == std or name.strip() in aliases:
                return std
        return name.strip()

    mapped_lines = [(map_channel(ch), url) for ch, url in valid_lines]

    # 分类输出
    category_result = []
    for cat, chs in CHANNEL_CATEGORIES.items():
        category_result.append(f"{cat},#genre#")
        for ch, url in mapped_lines:
            if ch in chs:
                category_result.append(f"{ch},{url}")

    with open(IPTV_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(category_result))

    print(f"✅ 第三阶段完成，已生成 IPTV.txt 共 {len(mapped_lines)} 条频道")

    os.system('git config --global user.name "github-actions"')
    os.system('git config --global user.email "github-actions@users.noreply.github.com"')
    os.system("git add IPTV.txt")
    os.system(f'git commit -m "自动更新 IPTV.txt（第 {run_count} 次）" || echo "⚠️ 无需提交"')
    os.system("git push origin main")