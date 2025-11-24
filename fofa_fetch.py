import os
import re
import requests
import time
import concurrent.futures
import subprocess
from datetime import datetime, timezone, timedelta

# ===============================
# 配置区
FOFA_URLS = {
    "https://fofa.info/result?qbase64=InVkcHh5IiAmJiBjb3VudHJ5PSJDTiI%3D": "ip.txt",
}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

COUNTER_FILE = "计数.txt"
IP_DIR = "ip"
RTP_DIR = "rtp"
ZUBO_FILE = "zubo.txt"
IPTV_FILE = "IPTV.txt"

# ===============================
# 分类与映射配置
CHANNEL_CATEGORIES = {
    "央视频道": [
        "CCTV1", "CCTV2"
    ],
    "卫视频道": [
        "湖南卫视", "浙江卫视"
    ],
    "数字频道": [
        "CHC动作电影", "CHC家庭影院"
    ],
}

# ===== 映射（别名 -> 标准名） =====
CHANNEL_MAPPING = {
    "CCTV1": ["CCTV-1", "CCTV-1 HD", "CCTV1 HD", "CCTV-1综合"],
    "CCTV2": ["CCTV-2", "CCTV-2 HD", "CCTV2 HD", "CCTV-2财经"],
}

# ===============================
# 计数逻辑（保留：记录运行次数，但不在 73 次时清空）
def get_run_count():
    if os.path.exists(COUNTER_FILE):
        try:
            return int(open(COUNTER_FILE, "r", encoding="utf-8").read().strip() or "0")
        except Exception:
            return 0
    return 0

def save_run_count(count):
    try:
        with open(COUNTER_FILE, "w", encoding="utf-8") as f:
            f.write(str(count))
    except Exception as e:
        print(f"⚠️ 写计数文件失败：{e}")

# ===============================
# IP 运营商判断（保留你的规则）
def get_isp(ip):
    # 注意：这些正则是示例，你可以根据需要调整 IP 段规则
    if re.match(r"^(1[0-9]{2}|2[0-3]{2}|42|43|58|59|60|61|110|111|112|113|114|115|116|117|118|119|120|121|122|123|124|125|126|127|175|180|182|183|184|185|186|187|188|189|223)\.", ip):
        return "电信"
    elif re.match(r"^(42|43|58|59|60|61|110|111|112|113|114|115|116|117|118|119|120|121|122|123|124|125|126|127|175|180|182|183|184|185|186|187|188|189|223)\.", ip):
        return "联通"
    elif re.match(r"^(223|36|37|38|39|100|101|102|103|104|105|106|107|108|109|134|135|136|137|138|139|150|151|152|157|158|159|170|178|182|183|184|187|188|189)\.", ip):
        return "移动"
    else:
        return "未知"

# ===============================
# 第一阶段
def first_stage():
    os.makedirs(IP_DIR, exist_ok=True)
    all_ips = set()

    for url, filename in FOFA_URLS.items():
        print(f"📡 正在爬取 {filename} ...")
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            urls_all = re.findall(r'<a href="http://(.*?)"', r.text)
            all_ips.update(u.strip() for u in urls_all if u.strip())
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
        except Exception as e:
            # 忽略单条 IP 出错，继续处理其余
            print(f"⚠️ 解析 IP {ip_port} 出错：{e}")
            continue

    # 更新运行计数（不做清空、不做重置）
    count = get_run_count() + 1
    save_run_count(count)
    mode = "a"   # 永远追加

    for filename, ip_set in province_isp_dict.items():
        path = os.path.join(IP_DIR, filename)
        try:
            with open(path, mode, encoding="utf-8") as f:
                for ip_port in sorted(ip_set):
                    f.write(ip_port + "\n")
            print(f"{path} 已追加写入 {len(ip_set)} 个 IP")
        except Exception as e:
            print(f"❌ 写入 {path} 失败：{e}")

    print(f"✅ 第一阶段完成，当前轮次：{count}")
    return count

# ===============================
# 第二阶段（组合 ip 与 rtp 生成 zubo.txt）
def second_stage():
    print("🔔 第二阶段触发：生成 zubo.txt")
    if not os.path.exists(IP_DIR):
        print("⚠️ ip 目录不存在，跳过第二阶段")
        return

    combined_lines = []
    # 确保 rtp 目录存在（若无程序按逻辑继续）
    if not os.path.exists(RTP_DIR):
        print("⚠️ rtp 目录不存在，无法进行第二阶段组合，跳过")
        return

    for ip_file in os.listdir(IP_DIR):
        if not ip_file.endswith(".txt"):
            continue
        ip_path = os.path.join(IP_DIR, ip_file)
        rtp_path = os.path.join(RTP_DIR, ip_file)
        if not os.path.exists(rtp_path):
            # 没有对应的 rtp 文件则跳过
            continue

        try:
            with open(ip_path, encoding="utf-8") as f1, open(rtp_path, encoding="utf-8") as f2:
                ip_lines = [x.strip() for x in f1 if x.strip()]
                rtp_lines = [x.strip() for x in f2 if x.strip()]
        except Exception as e:
            print(f"⚠️ 读取 {ip_path} 或 {rtp_path} 失败：{e}")
            continue

        if not ip_lines or not rtp_lines:
            continue

        for ip_port in ip_lines:
            for rtp_line in rtp_lines:
                if "," not in rtp_line:
                    continue
                ch_name, rtp_url = rtp_line.split(",", 1)
                # rtp_url 例如 rtp://239.x.x.x:xxxx/...  -> 取 rtp 后半部分
                # 保持原有组合形式： http://{ip_port}/rtp/{rtp_part}
                if "rtp://" in rtp_url:
                    rtp_part = rtp_url.split("rtp://", 1)[1]
                else:
                    # 如果不是以 rtp:// 开头，则直接使用后半部分（保守处理）
                    rtp_part = rtp_url
                combined_lines.append(f"{ch_name},http://{ip_port}/rtp/{rtp_part}")

    # 去重（按 URL 部分去重）
    unique = {}
    for line in combined_lines:
        if "," not in line:
            continue
        url_part = line.split(",", 1)[1]
        if url_part not in unique:
            unique[url_part] = line

    try:
        with open(ZUBO_FILE, "w", encoding="utf-8") as f:
            for line in unique.values():
                f.write(line + "\n")
        print(f"🎯 第二阶段完成，共 {len(unique)} 条有效 URL 写入 {ZUBO_FILE}")
    except Exception as e:
        print(f"❌ 写 zubo.txt 失败：{e}")

# ===============================
# 第三阶段（检测、生成 IPTV.txt，并写回可用 IP 到 ip/ 目录（覆盖））
def third_stage():
    print("🧩 第三阶段：多线程检测代表频道生成 IPTV.txt 并写回可用 IP 到 ip/目录（覆盖）")

    if not os.path.exists(ZUBO_FILE):
        print("⚠️ zubo.txt 不存在，跳过第三阶段")
        return

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

    # 别名映射
    alias_map = {}
    for main_name, aliases in CHANNEL_MAPPING.items():
        for alias in aliases:
            alias_map[alias] = main_name

    # 读取现有 ip 文件，建立 ip_port -> operator 映射
    ip_info = {}
    if os.path.exists(IP_DIR):
        for fname in os.listdir(IP_DIR):
            if not fname.endswith(".txt"):
                continue
            province_operator = fname.replace(".txt", "")
            try:
                with open(os.path.join(IP_DIR, fname), encoding="utf-8") as f:
                    for line in f:
                        ip_port = line.strip()
                        if ip_port:
                            ip_info[ip_port] = province_operator
            except Exception as e:
                print(f"⚠️ 读取 {fname} 失败：{e}")

    # 读取 zubo.txt 并按 ip:port 分组
    groups = {}
    with open(ZUBO_FILE, encoding="utf-8") as f:
        for line in f:
            if "," not in line:
                continue
            ch_name, url = line.strip().split(",", 1)
            ch_main = alias_map.get(ch_name, ch_name)
            m = re.match(r"http://(\d+\.\d+\.\d+\.\d+:\d+)/", url)
            if m:
                ip_port = m.group(1)
                groups.setdefault(ip_port, []).append((ch_main, url))

    # 选择代表频道并检测
    def detect_ip(ip_port, entries):
        # 优先检测 CCTV1 代表频道
        rep_channels = [u for c, u in entries if c == "CCTV1"]
        if not rep_channels and entries:
            rep_channels = [entries[0][1]]
        playable = any(check_stream(u) for u in rep_channels)
        return ip_port, playable

    print(f"🚀 启动多线程检测（共 {len(groups)} 个 IP）...")
    playable_ips = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(detect_ip, ip, chs): ip for ip, chs in groups.items()}
        for future in concurrent.futures.as_completed(futures):
            try:
                ip_port, ok = future.result()
            except Exception as e:
                print(f"⚠️ 线程检测返回异常：{e}")
                continue
            if ok:
                playable_ips.add(ip_port)

    print(f"✅ 检测完成，可播放 IP 共 {len(playable_ips)} 个")

    # 生成 valid_lines，并同时为写回 ip/ 目录准备 operator -> set(ip_port)
    valid_lines = []
    seen = set()
    operator_playable_ips = {}  # operator -> set of ip_port

    for ip_port in playable_ips:
        operator = ip_info.get(ip_port, "未知")

        for c, u in groups.get(ip_port, []):
            key = f"{c},{u}"
            if key not in seen:
                seen.add(key)
                valid_lines.append(f"{c},{u}${operator}")

                # 记录到 operator_playable_ips，用于覆盖写回文件
                operator_playable_ips.setdefault(operator, set()).add(ip_port)

    # 将可用 IP 覆盖写回对应的 ip/省份运营商.txt（覆盖整个文件）
    for operator, ip_set in operator_playable_ips.items():
        if operator == "未知":
            # 如果 operator 未知，可选择跳过或写入到 ip/未知.txt
            target_file = os.path.join(IP_DIR, "未知.txt")
        else:
            target_file = os.path.join(IP_DIR, operator + ".txt")
        try:
            os.makedirs(IP_DIR, exist_ok=True)
            with open(target_file, "w", encoding="utf-8") as wf:
                for ip in sorted(ip_set):
                    wf.write(ip + "\n")
            print(f"📥 覆盖写入 {target_file}，共 {len(ip_set)} 条可用 IP")
        except Exception as e:
            print(f"❌ 写回 {target_file} 失败：{e}")

    # 写 IPTV.txt（包含更新时间与分类）
    beijing_now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    disclaimer_url = "https://kakaxi-1.asia/LOGO/Disclaimer.mp4"

    try:
        with open(IPTV_FILE, "w", encoding="utf-8") as f:
            f.write(f"更新时间: {beijing_now}（北京时间）\n\n")
            f.write("更新时间,#genre#\n")
            f.write(f"{beijing_now},{disclaimer_url}\n\n")

            for category, ch_list in CHANNEL_CATEGORIES.items():
                f.write(f"{category},#genre#\n")
                for ch in ch_list:
                    for line in valid_lines:
                        name = line.split(",", 1)[0]
                        if name == ch:
                            f.write(line + "\n")
                f.write("\n")
        print(f"🎯 IPTV.txt 生成完成，共 {len(valid_lines)} 条频道")
    except Exception as e:
        print(f"❌ 写 IPTV.txt 失败：{e}")

# ===============================
# 文件推送
def push_all_files():
    print("🚀 推送所有更新文件到 GitHub...")
    try:
        os.system('git config --global user.name "github-actions"')
        os.system('git config --global user.email "github-actions@users.noreply.github.com"')
    except Exception:
        pass

    os.system("git add 计数.txt || true")
    os.system("git add ip/*.txt || true")
    os.system("git add IPTV.txt || true")
    os.system('git commit -m "自动更新：计数、IP文件、IPTV.txt" || echo "⚠️ 无需提交"')
    os.system("git push origin main || echo '⚠️ 推送失败'")

# ===============================
# 主执行逻辑
if __name__ == "__main__":
    # 确保目录存在
    os.makedirs(IP_DIR, exist_ok=True)
    os.makedirs(RTP_DIR, exist_ok=True)

    run_count = first_stage()

    # 每 12 的倍数执行第2和第3阶段（包括第12次、第24次等）
    if run_count % 12 == 0:
        second_stage()
        third_stage()
    else:
        print("ℹ️ 本次不是 12 的倍数，跳过第二、三阶段")

    push_all_files()
