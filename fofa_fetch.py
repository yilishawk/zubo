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
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

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
    "CCTV2": ["CCTV-2", "CCTV-2 HD", "CCTV2 HD", "CCTV-2财经", "CCTV2 720", "节目暂时不可用 1080"],
}

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
        print(f"📡 正在抓取 {filename} ...")
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            urls_all = re.findall(r'<a href="http://(.*?)"', r.text)
            all_ips.update(u.strip() for u in urls_all)
        except Exception as e:
            print(f"❌ 抓取失败：{e}")
        time.sleep(3)
    return all_ips

# ===============================
# 第二阶段：生成 zubo.txt（合并历史 IP + 新 IP）
def second_stage(new_ips):
    print("🔔 第二阶段：生成 zubo.txt")
    combined_lines = []

    # 遍历 ip 文件夹
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

        # 合并新抓 IP
        for ip_port in new_ips:
            if ip_port not in ip_lines:
                ip_lines.append(ip_port)

        for ip_port in ip_lines:
            for rtp_line in rtp_lines:
                if "," not in rtp_line:
                    continue
                ch_name, rtp_url = rtp_line.split(",", 1)
                combined_lines.append(f"{ch_name},http://{ip_port}/rtp/{rtp_url.split('rtp://')[1]}")

    # 去重
    unique = {}
    for line in combined_lines:
        url_part = line.split(",", 1)[1]
        if url_part not in unique:
            unique[url_part] = line

    with open(ZUBO_FILE, "w", encoding="utf-8") as f:
        for line in unique.values():
            f.write(line + "\n")
    print(f"🎯 第二阶段完成，共 {len(unique)} 条有效 URL")
    return unique.values()

# ===============================
# 第三阶段：多线程检测 + 生成 IPTV.txt + 更新 ip 文件（覆盖旧文件）
def third_stage(zubo_lines):
    print("🧩 第三阶段：多线程检测生成 IPTV.txt并更新 ip/*.txt")

    # ffprobe 检测函数
    def check_stream(url, timeout=5):
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_streams", "-i", url],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout + 2
            )
            return b"codec_type" in result.stdout
        except Exception:
            return False

    # 建立别名映射
    alias_map = {}
    for main_name, aliases in CHANNEL_MAPPING.items():
        for alias in aliases:
            alias_map[alias] = main_name

    # 按 IP 分组
    groups = {}
    for line in zubo_lines:
        if "," not in line:
            continue
        ch_name, url = line.strip().split(",", 1)
        ch_main = alias_map.get(ch_name, ch_name)
        m = re.match(r"http://(\d+\.\d+\.\d+\.\d+:\d+)/", url)
        if m:
            ip_port = m.group(1)
            groups.setdefault(ip_port, []).append((ch_main, url))

    # 多线程检测
    def detect_ip(ip_port, entries):
        rep_channels = [u for c, u in entries if c == "CCTV1"]
        if not rep_channels and entries:
            rep_channels = [entries[0][1]]
        playable = any(check_stream(u) for u in rep_channels)
        return ip_port, playable

    playable_ips = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(detect_ip, ip, chs): ip for ip, chs in groups.items()}
        for future in concurrent.futures.as_completed(futures):
            ip_port, ok = future.result()
            if ok:
                playable_ips.add(ip_port)

    # 生成最终去重 IPTV 列表 & 更新 ip/*.txt
    valid_lines = []
    ip_save_dict = {}

    for ip_port in playable_ips:
        # 取省份运营商
        ip_only = ip_port.split(":")[0]
        isp = get_isp(ip_only)
        province_operator = f"{isp}" if isp != "未知" else "未知"
        ip_save_dict.setdefault(province_operator, set()).add(ip_port)
        for c, u in groups[ip_port]:
            key = f"{c},{u}"
            valid_lines.append(f"{c},{u}${province_operator}")

    # 写 IPTV.txt
    with open(IPTV_FILE, "w", encoding="utf-8") as f:
        for category, ch_list in CHANNEL_CATEGORIES.items():
            f.write(f"{category},#genre#\n")
            for ch in ch_list:
                for line in valid_lines:
                    name = line.split(",", 1)[0]
                    if name == ch:
                        f.write(line + "\n")
            f.write("\n")

    # 清空并重建 ip 文件夹
    if os.path.exists(IP_DIR):
        for f in os.listdir(IP_DIR):
            os.remove(os.path.join(IP_DIR, f))
    else:
        os.makedirs(IP_DIR)

    # 写可用 IP 到 ip/*.txt
    for province_operator, ips in ip_save_dict.items():
        path = os.path.join(IP_DIR, f"{province_operator}.txt")
        with open(path, "w", encoding="utf-8") as f:
            for ip in sorted(ips):
                f.write(ip + "\n")

    print(f"🎯 IPTV.txt 生成完成，共 {len(valid_lines)} 条频道")
    print(f"✅ ip 文件更新完成，共 {len(ip_save_dict)} 个省份运营商")

# ===============================
# ===============================
# 文件推送
def push_all_files():
    print("🚀 推送更新到 GitHub（覆盖旧文件）...")
    os.system('git config --global user.name "github-actions"')
    os.system('git config --global user.email "github-actions@users.noreply.github.com"')
    os.system("git add -A")
    os.system('git commit -m "自动更新 IPTV.txt 与可用 IP" || echo "⚠️ 无需提交"')
    os.system("git push origin main --force || echo '⚠️ 推送失败'")
# ===============================
# 主执行逻辑
if __name__ == "__main__":
    new_ips = first_stage()
    zubo_lines = second_stage(new_ips)
    third_stage(zubo_lines)
    push_all_files()