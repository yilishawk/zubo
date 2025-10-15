import os
import re
import time
import random
import requests
import concurrent.futures
import subprocess

# ===============================
# 配置
FOFA_URLS = {
    "https://fofa.info/result?qbase64=InVkcHh5IiAmJiBjb3VudHJ5PSJDTiI%3D": "ip.txt",
}
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

COUNTER_FILE = "计数.txt"
IP_DIR = "ip"
RTP_DIR = "rtp"
ZUBO_FILE = "zubo.txt"
IPTV_FILE = "IPTV.txt"

CHANNEL_CATEGORIES = {
    "央视频道": ["CCTV1", "CCTV2"],
    "卫视频道": ["湖南卫视", "浙江卫视"],
    "数字频道": ["CHC动作电影", "CHC家庭影院", "CHC影迷电影"],
}

CHANNEL_MAPPING = {
    "CCTV1": ["CCTV-1", "CCTV-1 HD", "CCTV1 HD", "CCTV-1综合"],
    "CCTV2": ["CCTV-2", "CCTV-2 HD", "CCTV2 HD", "CCTV-2财经"],
    "湖南卫视": ["湖南", "湖南HD", "湖南卫视高清"],
    "浙江卫视": ["浙江", "浙江HD", "浙江卫视高清"],
    "CHC动作电影": ["CHC动作", "CHC动作HD"],
    "CHC家庭影院": ["CHC家庭", "CHC家庭HD"],
    "CHC影迷电影": ["CHC影迷", "CHC影迷HD"],
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
    open(COUNTER_FILE, "w").write(str(count))

def check_and_clear_files_by_run_count():
    os.makedirs(IP_DIR, exist_ok=True)
    count = get_run_count() + 1
    if count >= 73:
        print(f"🧹 第 {count} 次运行，清空 {IP_DIR} 下所有 .txt 文件")
        for f in os.listdir(IP_DIR):
            if f.endswith(".txt"):
                os.remove(os.path.join(IP_DIR, f))
        save_run_count(1)
        return "w", 1
    else:
        save_run_count(count)
        return "a", count

# ===============================
# IP 运营商判断
def get_isp(ip):
    if ip.startswith(("113.", "116.", "117.", "118.", "119.")):
        return "电信"
    elif ip.startswith(("36.", "39.", "42.", "43.", "58.")):
        return "联通"
    elif ip.startswith(("100.", "101.", "102.", "103.", "104.", "223.")):
        return "移动"
    return "未知"

# ===============================
# 第一阶段：抓取 IP
def first_stage():
    all_ips = set()
    for url, filename in FOFA_URLS.items():
        print(f"📡 正在爬取 {filename} ...")
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            urls_all = re.findall(r'<a href="http://(.*?)"', r.text)
            all_ips.update(u.strip() for u in urls_all)
        except Exception as e:
            print(f"❌ 爬取失败：{e}")
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
        print(f"{path} 已{'覆盖' if mode=='w' else '追加'}写入 {len(ip_set)} 个 IP")
    print(f"✅ 第一阶段完成，当前轮次：{run_count}")
    return run_count

# ===============================
# 第二阶段：生成 zubo.txt
def second_stage():
    print("🔔 第二阶段触发：生成 zubo.txt")
    combined_lines = []
    for ip_file in os.listdir(IP_DIR):
        if not ip_file.endswith(".txt"):
            continue
        ip_path = os.path.join(IP_DIR, ip_file)
        rtp_path = os.path.join(RTP_DIR, ip_file)
        if not os.path.exists(rtp_path):
            continue

        with open(ip_path, encoding="utf-8") as f1, open(rtp_path, encoding="utf-8") as f2:
            ip_lines = [x.strip() for x in f1 if x.strip()]
            rtp_lines = [x.strip() for x in f2 if x.strip()]

        for ip_port in ip_lines:
            for rtp_line in rtp_lines:
                if "," not in rtp_line:
                    continue
                ch_name, rtp_url = rtp_line.split(",", 1)
                combined_lines.append(f"{ch_name},{'http://' + ip_port + '/rtp/' + rtp_url.split('rtp://')[1]}")

    unique = {}
    for line in combined_lines:
        url = line.split(",", 1)[1]
        if url not in unique:
            unique[url] = line

    with open(ZUBO_FILE, "w", encoding="utf-8") as f:
        for line in unique.values():
            f.write(line + "\n")

    os.system("git add zubo.txt")
    os.system('git commit -m "自动更新 zubo.txt" || echo "⚠️ 无需提交"')
    os.system("git push origin main")
    print(f"🎯 第二阶段完成，zubo.txt 共 {len(unique)} 条 URL")

# ===============================
# 第三阶段：检测 + 测速 + 分类排序
def normalize_channel_name(name):
    for std, aliases in CHANNEL_MAPPING.items():
        for alias in aliases:
            if alias.lower() in name.lower():
                return std
    return name.strip()

def ffprobe_check(url, timeout=5):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-i", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout
        )
        return b"codec_type" in result.stdout
    except Exception:
        return False

def test_latency(url):
    start = time.time()
    try:
        r = requests.get(url, timeout=3, stream=True)
        next(r.iter_content(1))
        return time.time() - start
    except Exception:
        return 999
    finally:
        try:
            r.close()
        except:
            pass

def third_stage():
    print("🧩 第三阶段开始：CCTV1 检测 + 湖南卫视测速 + 分类排序")
    if not os.path.exists(ZUBO_FILE):
        print("⚠️ 未找到 zubo.txt，跳过")
        return

    with open(ZUBO_FILE, encoding="utf-8") as f:
        lines = [x.strip() for x in f if x.strip() and "," in x]

    mapped = [(normalize_channel_name(x.split(",", 1)[0]), x.split(",", 1)[1]) for x in lines]

    ip_groups = {}
    for ch, url in mapped:
        m = re.search(r"http://(.*?)/", url)
        if not m:
            continue
        ip = m.group(1)
        ip_groups.setdefault(ip, []).append((ch, url))

    valid_ips = []

    # ---- Step 1: CCTV1 检测 ----
    def check_ip(ip, entries):
        rep_urls = [url for ch, url in entries if ch == "CCTV1"]
        if not rep_urls:
            return None
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as exe:
            res = list(exe.map(ffprobe_check, rep_urls))
        if any(res):
            return ip, entries
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(check_ip, ip, entries) for ip, entries in ip_groups.items()]
        for fut in concurrent.futures.as_completed(futures):
            r = fut.result()
            if r:
                valid_ips.append(r)

    # ---- Step 2: 测速 ----
    ip_speeds = []

    def speed_test(ip, entries):
        rep_urls = [url for ch, url in entries if ch == "湖南卫视"]
        if not rep_urls:
            rep_urls = [entries[0][1]]  # 随机选择一个
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as exe:
            speeds = list(exe.map(test_latency, rep_urls))
        return (ip, min(speeds))

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(speed_test, ip, entries) for ip, entries in valid_ips]
        for fut in concurrent.futures.as_completed(futures):
            ip, spd = fut.result()
            ip_speeds.append((ip, spd))

    ip_speeds.sort(key=lambda x: x[1])

    # ---- Step 3: 分类输出 ----
    category_map = {cat: [] for cat in CHANNEL_CATEGORIES.keys()}
    for ip, _ in ip_speeds:
        for ch, url in ip_groups[ip]:
            for cat, names in CHANNEL_CATEGORIES.items():
                if ch in names:
                    category_map[cat].append(f"{ch},{url}")
                    break

    with open(IPTV_FILE, "w", encoding="utf-8") as f:
        for cat, lst in category_map.items():
            f.write(f"{cat},#genre#\n")
            for line in sorted(set(lst)):
                f.write(line + "\n")
            f.write("\n")

    os.system("git add IPTV.txt")
    os.system('git commit -m "自动更新 IPTV.txt" || echo "⚠️ 无需提交"')
    os.system("git push origin main")
    print(f"✅ 第三阶段完成，生成 IPTV.txt 共 {sum(len(v) for v in category_map.values())} 条频道")

# ===============================
# 主流程
if __name__ == "__main__":
    run_count = first_stage()
    if run_count in [12, 24, 36, 48, 60, 72]:
        second_stage()
        third_stage()