import os
import re
import requests
import time
import concurrent.futures
import socket
import struct

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

# 频道分类
CHANNEL_CATEGORIES = {
    "央视频道": ["CCTV1", "CCTV2"],
    "卫视频道": ["湖南卫视", "浙江卫视"],
    "数字频道": ["CHC动作电影", "CHC家庭影院", "CHC影迷电影"]
}

# 频道映射
CHANNEL_MAPPING = {
    "CCTV1": ["CCTV-1", "CCTV-1 HD", "CCTV1 HD", "CCTV-1综合", "CCTV1 4M1080", "CCTV1 5M1080HEVC"],
    "CCTV2": ["CCTV-2", "CCTV-2 HD", "CCTV2 HD", "CCTV-2财经", "CCTV2 720", "节目暂时不可用 1080"],
    "湖南卫视": ["湖南卫视", "Hunan TV"],
    "浙江卫视": ["浙江卫视", "Zhejiang TV"],
    "CHC动作电影": ["CHC动作电影"],
    "CHC家庭影院": ["CHC家庭影院"],
    "CHC影迷电影": ["CHC影迷电影"]
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
        page_content = resp.text
        pattern = r'<a href="http://(.*?)" target="_blank">'
        urls_all = re.findall(pattern, page_content)
        for u in urls_all:
            all_ips.add(u.strip())
    except Exception as e:
        print(f"{filename} 爬取失败：{e}")
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
        continue

write_mode, run_count = check_and_clear_files_by_run_count()

for filename, ip_set in province_isp_dict.items():
    save_path = os.path.join(IP_DIR, filename)
    with open(save_path, write_mode, encoding="utf-8") as f:
        for ip_port in sorted(ip_set):
            f.write(ip_port + "\n")

# ===============================
# 第二阶段：每 12,24,36,48,60,72 次生成 zubo.txt（不推送）
if run_count in [12,24,36,48,60,72]:
    combined_lines = []
    for ip_file in os.listdir(IP_DIR):
        if not ip_file.endswith(".txt"):
            continue
        ip_path = os.path.join(IP_DIR, ip_file)
        rtp_path = os.path.join(RTP_DIR, ip_file)
        if not os.path.exists(rtp_path):
            continue
        province_operator = ip_file.replace(".txt","")
        with open(ip_path,"r",encoding="utf-8") as f_ip, open(rtp_path,"r",encoding="utf-8") as f_rtp:
            ip_lines = [line.strip() for line in f_ip if line.strip()]
            rtp_lines = [line.strip() for line in f_rtp if line.strip()]
        if not ip_lines or not rtp_lines:
            continue
        first_rtp_line = rtp_lines[0]
        channel_name, rtp_url = first_rtp_line.split(",",1)
        # 检测第一个频道
        def build_and_check(ip_port):
            try:
                url = f"http://{ip_port}/rtp/{rtp_url.split('rtp://')[1]}"
                # 简单 TCP 测试端口是否能连通
                host, port = ip_port.split(":")
                port = int(port)
                s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                s.settimeout(3)
                s.connect((host,port))
                s.close()
                return f"{channel_name},{url}"
            except Exception:
                return None
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(build_and_check, ip_lines))
        valid_urls = [r for r in results if r]
        for idx,res in enumerate(valid_urls,start=1):
            suffix = f"${province_operator}{idx}"
            combined_lines.append(f"{res}{suffix}")
        # 组合其他频道
        for i, ip_port in enumerate(ip_lines,start=1):
            suffix = f"${province_operator}{i}"
            for other_rtp_line in rtp_lines[1:]:
                ch_name, rtp_url_rest = other_rtp_line.split(",",1)
                combined_lines.append(f"{ch_name},http://{ip_port}/rtp/{rtp_url_rest.split('rtp://')[1]}{suffix}")
    # 去重
    unique_lines = {}
    for line in combined_lines:
        parts = line.split(",",1)
        if len(parts)==2:
            url_part = parts[1].split("$")[0]
            if url_part not in unique_lines:
                unique_lines[url_part]=line
    combined_lines = list(unique_lines.values())
    # 写本地 zubo.txt
    with open(ZUBO_FILE,"w",encoding="utf-8") as f:
        for line in combined_lines:
            f.write(line+"\n")

# ===============================
# 第三阶段：检测 zubo.txt 并生成 IPTV.txt
if os.path.exists(ZUBO_FILE):
    with open(ZUBO_FILE,"r",encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    # 分组：同 IP 下的所有频道
    ip_group = {}
    for line in lines:
        ch,url = line.split(",",1)
        ip_key = url.split("$")[1][:-1]  # 广东电信1 -> 广东电信
        ip_group.setdefault(ip_key,[]).append((ch,url))
    # 检测同 ip 的 CCTV1
    def check_multicast(url):
        try:
            # rtp:// 检测
            match = re.search(r'(?:udp|rtp)://([\d\.]+):(\d+)',url)
            if match:
                host = match.group(1)
                port = int(match.group(2))
                s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
                s.settimeout(2)
                s.sendto(b"test", (host, port))
                s.close()
                return True
        except:
            return False
        return False
    valid_lines = []
    for ip_key, lst in ip_group.items():
        # 先检测 CCTV1，只要有一个通过则整个IP组有效
        cctv1_urls = [url for ch,url in lst if ch=="CCTV1"]
        ip_ok = any(check_multicast(u) for u in cctv1_urls)
        if ip_ok:
            valid_lines.extend(lst)
    # 映射频道名
    final_lines = []
    for ch,url in valid_lines:
        mapped_ch = ch
        for key,aliases in CHANNEL_MAPPING.items():
            if ch in aliases:
                mapped_ch = key
                break
        final_lines.append((mapped_ch,url))
    # 分类排序
    output_lines = []
    for cat, cat_list in CHANNEL_CATEGORIES.items():
        output_lines.append(f"{cat},#genre#")
        for ch in cat_list:
            for mch, url in final_lines:
                if mch==ch:
                    output_lines.append(f"{mch},{url}")
    # 写 IPTV.txt 并推送
    with open(IPTV_FILE,"w",encoding="utf-8") as f:
        for line in output_lines:
            f.write(line+"\n")
    # 推送仓库
    os.system('git config --global user.name "github-actions"')
    os.system('git config --global user.email "github-actions@users.noreply.github.com"')
    os.system("git add IPTV.txt")
    os.system(f'git commit -m "自动更新 IPTV.txt {time.strftime("%Y-%m-%d %H:%M:%S")}' + '" || echo "⚠️ 无需提交"')
    os.system("git push origin main")