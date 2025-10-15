import os
import re
import requests
import time
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
IPTV_FILE = "IPTV.txt"

# 频道分类与映射
CHANNEL_CATEGORIES = {
    "央视频道": ["CCTV1", "CCTV2"],
    "卫视频道": ["湖南卫视", "浙江卫视"],
    "数字频道": ["CHC动作电影", "CHC家庭影院", "CHC影迷电影"]
}

CHANNEL_MAPPING = {
    "CCTV1": ["CCTV-1", "CCTV-1 HD", "CCTV1 HD", "CCTV-1综合", "CCTV1 4M1080", "CCTV1 5M1080HEVC"],
    "CCTV2": ["CCTV-2", "CCTV-2 HD", "CCTV2 HD", "CCTV-2财经", "CCTV2 720", "节目暂时不可用 1080"],
    # 可根据实际添加其他频道映射
}

# ===============================
# 计数管理
def get_run_count():
    if os.path.exists(COUNTER_FILE):
        try:
            with open(COUNTER_FILE, "r", encoding="utf-8") as f:
                return int(f.read().strip())
        except:
            return 0
    return 0

def save_run_count(count):
    with open(COUNTER_FILE, "w", encoding="utf-8") as f:
        f.write(str(count))

def check_and_clear_files_by_run_count():
    """
    每运行73次清空 IP_DIR 下所有 txt 文件。
    前72次追加，第73次清空覆盖。
    返回写入模式 w 或 a
    """
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
        resp = requests.get(url, headers=HEADERS, timeout=15)
        urls_all = re.findall(r'<a href="http://(.*?)" target="_blank">', resp.text)
        for u in urls_all:
            all_ips.add(u.strip())
    except Exception as e:
        print(f"爬取 {filename} 失败：{e}")
    time.sleep(1)

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
        time.sleep(0.3)
    except:
        continue

write_mode, run_count = check_and_clear_files_by_run_count()
for filename, ip_set in province_isp_dict.items():
    save_path = os.path.join(IP_DIR, filename)
    with open(save_path, write_mode, encoding="utf-8") as f:
        for ip_port in sorted(ip_set):
            f.write(ip_port + "\n")

# ===============================
# 第二阶段：每 12、24、36、48、60、72 次触发 zubo.txt
if run_count in [12, 24, 36, 48, 60, 72]:
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

        # 检测第一个 RTP
        def build_and_check(ip_port):
            try:
                first_rtp_line = rtp_lines[0]
                ch_name, rtp_url = first_rtp_line.split(",", 1)
                url = f"http://{ip_port}/rtp/{rtp_url.split('rtp://')[1]}"
                resp = requests.get(url, timeout=5, stream=True)
                if resp.status_code == 200:
                    return f"{ch_name},{url}${province_operator}{ip_lines.index(ip_port)+1}"
            except:
                pass
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(build_and_check, ip_lines))

        valid_urls = [r for r in results if r]
        combined_lines.extend(valid_urls)

        # 组合其他频道（不检测）
        for i, ip_port in enumerate(ip_lines, start=1):
            suffix = f"${province_operator}{i}"
            for other_rtp_line in rtp_lines[1:]:
                ch_name, rtp_url_rest = other_rtp_line.split(",", 1)
                combined_lines.append(f"{ch_name},http://{ip_port}/rtp/{rtp_url_rest.split('rtp://')[1]}{suffix}")

    # 去重
    unique_lines = {}
    for line in combined_lines:
        parts = line.split(",", 1)
        if len(parts) == 2:
            url_part = parts[1].split("$")[0]
            if url_part not in unique_lines:
                unique_lines[url_part] = line
    combined_lines = list(unique_lines.values())

    # 写入 zubo.txt（不推送）
    with open(ZUBO_FILE, "w", encoding="utf-8") as f:
        for line in combined_lines:
            f.write(line + "\n")

# ===============================
# 第三阶段：检测 zubo.txt 并生成 IPTV.txt
if os.path.exists(ZUBO_FILE):
    with open(ZUBO_FILE, "r", encoding="utf-8") as f:
        zubo_lines = [line.strip() for line in f if line.strip()]

    # 按 IP 分组
    ip_to_lines = {}
    for line in zubo_lines:
        parts = line.split(",", 1)
        if len(parts) != 2:
            continue
        url_with_suffix = parts[1]
        m = re.match(r"http://([\d\.]+):\d+/", url_with_suffix)
        if m:
            ip_str = m.group(1)
            ip_to_lines.setdefault(ip_str, []).append(line)

    # 检测同 IP 下的 CCTV1，只要有一个 CCTV1 成功就保留全部
    def check_ip(lines):
        cctv1_lines = [l for l in lines if l.startswith("CCTV1,")]
        for line in cctv1_lines:
            url_part = line.split(",", 1)[1].split("$")[0]
            try:
                resp = requests.get(url_part, timeout=5, stream=True)
                if resp.status_code == 200:
                    return lines
            except:
                continue
        return []

    final_lines = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(check_ip, ip_to_lines.values()))
    for res in results:
        final_lines.extend(res)

    # 映射频道别名到标准名
    mapped_lines = []
    for line in final_lines:
        ch, url_sfx = line.split(",", 1)
        for std_ch, aliases in CHANNEL_MAPPING.items():
            if ch in aliases:
                ch = std_ch
                break
        mapped_lines.append(f"{ch},{url_sfx}")

    # 按分类排序，并在每类前加 #genre#
    sorted_lines = []
    for cat, ch_list in CHANNEL_CATEGORIES.items():
        sorted_lines.append(f"{cat},#genre#")
        for ch in ch_list:
            for line in mapped_lines:
                if line.startswith(ch + ","):
                    sorted_lines.append(line)

    # 写入 IPTV.txt 并推送
    with open(IPTV_FILE, "w", encoding="utf-8") as f:
        for line in sorted_lines:
            f.write(line + "\n")

    os.system('git config --global user.name "github-actions"')
    os.system('git config --global user.email "github-actions@users.noreply.github.com"')
    os.system(f"git add {IPTV_FILE}")
    os.system(f'git commit -m "自动更新 {IPTV_FILE} {time.strftime("%Y-%m-%d %H:%M:%S")}" || echo "⚠️ 无需提交"')
    os.system(f"git push origin main")