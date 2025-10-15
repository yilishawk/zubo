import os
import re
import requests
import time
import concurrent.futures
import subprocess

# ===============================
# 配置区
FOFA_URLS = {
    "https://fofa.info/result?qbase64=InVkcHh5IiAmJiBjb3VudHJ5PSJDTiI%3D": "ip.txt",
}
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

COUNTER_FILE = "计数.txt"
IP_DIR = "ip"
RTP_DIR = "rtp"
ZUBO_FILE = "zubo.txt"
IPTV_FILE = "IPTV.txt"

# ===============================
# 分类与映射配置
CHANNEL_CATEGORIES = {
    "央视频道": ["CCTV1", "CCTV2"],
    "卫视频道": ["湖南卫视", "浙江卫视"],
    "数字频道": ["CHC动作电影", "CHC家庭影院", "CHC影迷电影"],
}
CHANNEL_MAPPING = {
    "CCTV1": ["CCTV-1", "CCTV-1 HD", "CCTV1 HD", "CCTV-1综合", "CCTV1 4M1080", "CCTV1 5M1080HEVC"],
    "CCTV2": ["CCTV-2", "CCTV-2 HD", "CCTV2 HD", "CCTV-2财经", "CCTV2 720"],
    "湖南卫视": ["湖南", "湖南HD", "湖南卫视高清"],
    "浙江卫视": ["浙江", "浙江HD", "浙江卫视高清"],
    "CHC动作电影": ["CHC动作", "CHC动作HD"],
    "CHC家庭影院": ["CHC家庭", "CHC家庭HD"],
    "CHC影迷电影": ["CHC影迷", "CHC影迷HD"]
}

# ===============================
# 计数逻辑
def get_run_count():
    if os.path.exists(COUNTER_FILE):
        try:
            return int(open(COUNTER_FILE).read().strip())
        except:
            return 0
    return 0

def save_run_count(count):
    with open(COUNTER_FILE, "w", encoding="utf-8") as f:
        f.write(str(count))

def check_and_clear_files_by_run_count():
    os.makedirs(IP_DIR, exist_ok=True)
    count = get_run_count() + 1
    if count >= 73:
        for f in os.listdir(IP_DIR):
            if f.endswith(".txt"):
                os.remove(os.path.join(IP_DIR, f))
        save_run_count(1)
        return "w", 1
    else:
        save_run_count(count)
        return "a", count

# ===============================
# IP运营商判断
def get_isp(ip):
    if ip.startswith(("113.", "116.", "117.", "118.", "119.")):
        return "电信"
    elif ip.startswith(("36.", "39.", "42.", "43.", "58.")):
        return "联通"
    elif ip.startswith(("100.", "101.", "102.", "103.", "104.", "223.")):
        return "移动"
    return "未知"

# ===============================
# 第一阶段：抓取IP
def first_stage():
    all_ips = set()
    for url, filename in FOFA_URLS.items():
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            urls_all = re.findall(r'<a href="http://(.*?)"', r.text)
            all_ips.update(u.strip() for u in urls_all)
        except Exception as e:
            print(f"❌ 爬取失败 {filename}: {e}")
        time.sleep(3)

    province_isp_dict = {}
    for ip_port in all_ips:
        try:
            ip = ip_port.split(":")[0]
            res = requests.get(f"http://ip-api.com/json/{ip}?lang=zh-CN", timeout=10)
            data = res.json()
            province = data.get("regionName", "未知")
            isp = get_isp(ip)
            if isp == "未知":
                continue
            fname = f"{province}{isp}.txt"
            province_isp_dict.setdefault(fname, set()).add(ip_port)
        except Exception:
            continue

    mode, run_count = check_and_clear_files_by_run_count()
    for filename, ip_set in province_isp_dict.items():
        path = os.path.join(IP_DIR, filename)
        with open(path, mode, encoding="utf-8") as f:
            for ip_port in sorted(ip_set):
                f.write(ip_port + "\n")
    return run_count

# ===============================
# 第二阶段：ffprobe检测CCTV1,生成 zubo.txt
def check_stream_ffprobe(url, timeout=5):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=index", "-i", url],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout+2
        )
        return b"index" in result.stdout
    except:
        return False

def second_stage():
    combined = []
    for ip_file in os.listdir(IP_DIR):
        if not ip_file.endswith(".txt"):
            continue
        ip_path = os.path.join(IP_DIR, ip_file)
        rtp_path = os.path.join(RTP_DIR, ip_file)
        if not os.path.exists(rtp_path):
            continue
        province_operator = ip_file.replace(".txt", "")
        with open(ip_path, encoding="utf-8") as f1, open(rtp_path, encoding="utf-8") as f2:
            ips = [x.strip() for x in f1 if x.strip()]
            channels = [x.strip() for x in f2 if x.strip()]
        if not ips or not channels:
            continue

        # 多线程检测CCTV1
        def test_ip(ip_port):
            cctv1_urls = []
            for ch_line in channels:
                if "," not in ch_line:
                    continue
                ch_name, rtp_url = ch_line.split(",", 1)
                if "CCTV1" in ch_name:
                    full_url = f"http://{ip_port}/rtp/{rtp_url.split('rtp://')[1]}"
                    cctv1_urls.append(full_url)
            if not cctv1_urls:
                return None
            playable = any(check_stream_ffprobe(u) for u in cctv1_urls)
            if playable:
                # CCTV1可播，保留全部频道
                ip_entries = []
                for ch_line in channels:
                    if "," not in ch_line:
                        continue
                    ch_name, rtp_url = ch_line.split(",", 1)
                    ip_entries.append(f"{ch_name},http://{ip_port}/rtp/{rtp_url.split('rtp://')[1]}")
                return ip_entries
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as exe:
            results = exe.map(test_ip, ips)
            for r in results:
                if r:
                    combined.extend(r)

    # 去重
    unique = {}
    for line in combined:
        url_part = line.split(",", 1)[1]
        if url_part not in unique:
            unique[url_part] = line

    with open(ZUBO_FILE, "w", encoding="utf-8") as f:
        for line in unique.values():
            f.write(line + "\n")

    # 推送 zubo.txt
    os.system('git config --global user.name "github-actions"')
    os.system('git config --global user.email "github-actions@users.noreply.github.com"')
    os.system(f"git add {ZUBO_FILE}")
    os.system(f'git commit -m "自动更新 {ZUBO_FILE}" || echo "无改动"')
    os.system("git push origin main")

# ===============================
# 第三阶段：从 zubo.txt 分类排序生成 IPTV.txt，代表频道测速多线程
def third_stage():
    if not os.path.exists(ZUBO_FILE):
        return
    with open(ZUBO_FILE, encoding="utf-8") as f:
        lines = [x.strip() for x in f if x.strip()]
    # 按 IP 分组
    ip_groups = {}
    for line in lines:
        if "," not in line:
            continue
        ch, url = line.split(",", 1)
        ip_match = re.search(r"http://(.*?)/", url)
        if ip_match:
            ip = ip_match.group(1)
            ip_groups.setdefault(ip, []).append((ch, url))

    # 代表频道测速（湖南卫视）
    def test_latency(url):
        start = time.time()
        try:
            r = requests.get(url, timeout=5, stream=True)
            if r.status_code == 200:
                return time.time() - start
        except:
            return None
        return None

    def test_ip_group(ip, entries):
        rep_url = None
        for ch, url in entries:
            if "湖南卫视" in ch:
                rep_url = url
                break
        if not rep_url:
            return ip, float("inf"), entries
        latency = test_latency(rep_url)
        if latency is None:
            latency = float("inf")
        return ip, latency, entries

    valid_groups = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as exe:
        futures = [exe.submit(test_ip_group, ip, entries) for ip, entries in ip_groups.items()]
        for future in concurrent.futures.as_completed(futures):
            ip, latency, entries = future.result()
            if latency != float("inf"):
                valid_groups.append((latency, entries))

    # 排序按延迟
    valid_groups.sort(key=lambda x: x[0])

    # 分类输出 IPTV.txt
    category_map = {cat: [] for cat in CHANNEL_CATEGORIES}
    for _, entries in valid_groups:
        for ch, url in entries:
            std_name = next((k for k, v in CHANNEL_MAPPING.items() if ch in v or ch == k), ch)
            for cat, names in CHANNEL_CATEGORIES.items():
                if std_name in names:
                    category_map[cat].append(f"{std_name},{url}")
                    break

    with open(IPTV_FILE, "w", encoding="utf-8") as f:
        for cat, lines in category_map.items():
            f.write(f"{cat},#genre#\n")
            for line in sorted(set(lines)):
                f.write(line + "\n")
            f.write("\n")

    # 推送 IPTV.txt
    os.system(f"git add {IPTV_FILE}")
    os.system(f'git commit -m "自动更新 {IPTV_FILE}" || echo "无改动"')
    os.system("git push origin main")

# ===============================
# 主执行逻辑
if __name__ == "__main__":
    run_count = first_stage()
    # 第二阶段触发条件
    if run_count in [12, 24, 36, 48, 60, 72]:
        second_stage()
        third_stage()