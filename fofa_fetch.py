import os
import re
import requests
import concurrent.futures
from datetime import datetime

# ===== 路径配置 =====
IP_FOLDER = "ip"
RTP_FOLDER = "rtp"
OUTPUT_FILE = "iptv.txt"
COUNTER_FILE = "计数.txt"

# ===== 检测配置 =====
CHECK_CHANNEL = "CCTV1"
MAX_WORKERS = 20
TIMEOUT = 2
IP_API_URL = "http://ip-api.com/json/"

# ========== 工具函数 ==========
def get_isp(ip):
    """根据 IP 段判断运营商（本地规则）"""
    try:
        if re.match(r"^(1[0-9]{2}|2[0-3]{2}|42|43|58|59|60|61|110|111|112|113|114|115|116|117|118|119|120|121|122|123|124|125|126|127|175|180|182|183|184|185|186|187|188|189|223)\.", ip):
            return "电信"
        elif re.match(r"^(42|43|58|59|60|61|110|111|112|113|114|115|116|117|118|119|120|121|122|123|124|125|126|127|175|180|182|183|184|185|186|187|188|189|223)\.", ip):
            return "联通"
        elif re.match(r"^(223|36|37|38|39|100|101|102|103|104|105|106|107|108|109|134|135|136|137|138|139|150|151|152|157|158|159|170|178|182|183|184|187|188|189)\.", ip):
            return "移动"
        else:
            return "未知"
    except:
        return "未知"

def get_province(ip):
    """通过 ip-api.com 获取省份"""
    try:
        res = requests.get(IP_API_URL + ip, timeout=3)
        data = res.json()
        if data.get("status") == "success":
            return data.get("regionName", "未知")
        else:
            return "未知"
    except:
        return "未知"

def detect_channel(ip, port, channel_url):
    """检测该 IP:port 的 CCTV1 是否可用"""
    test_url = channel_url.replace("rtp://", f"http://{ip}:{port}/")
    try:
        r = requests.get(test_url, timeout=TIMEOUT, stream=True)
        return r.status_code == 200
    except:
        return False

def detect_ip(ip_info):
    """多线程检测任务"""
    ip, province, isp = ip_info
    province_isp = f"{province}{isp}"
    rtp_file = os.path.join(RTP_FOLDER, f"{province_isp}.txt")

    if not os.path.exists(rtp_file):
        print(f"⚠️ {province_isp} 没有 RTP 文件，跳过")
        return None

    with open(rtp_file, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    cctv1_lines = [l for l in lines if CHECK_CHANNEL in l]
    test_line = cctv1_lines[0] if cctv1_lines else (lines[0] if lines else None)
    if not test_line:
        print(f"⚠️ {province_isp} RTP 文件为空，跳过")
        return None

    match = re.search(r"rtp://([0-9.:]+)", test_line)
    if not match:
        print(f"⚠️ {province_isp} RTP 文件格式错误，跳过")
        return None

    port = match.group(1).split(":")[-1]
    if detect_channel(ip, port, test_line):
        return province_isp, f"{ip}:{port}"
    return None

# ========== 第一阶段 ==========
def stage_one(new_ips):
    """抓取 + 分类 + 检测 + 更新 ip 文件夹"""
    all_ips = {}  # {省份运营商: [ip1, ip2, ...]}

    # ---- Step1: 分类新IP ----
    for ip in new_ips:
        isp = get_isp(ip)
        province = get_province(ip)
        province_isp = f"{province}{isp}"
        if province_isp not in all_ips:
            all_ips[province_isp] = []
        all_ips[province_isp].append(ip)

    # ---- Step2: 合并旧IP ----
    if not os.path.exists(IP_FOLDER):
        os.makedirs(IP_FOLDER)

    for province_isp, ip_list in all_ips.items():
        ip_file = os.path.join(IP_FOLDER, f"{province_isp}.txt")
        if os.path.exists(ip_file):
            with open(ip_file, "r", encoding="utf-8") as f:
                old_ips = [line.strip() for line in f if line.strip()]
            ip_list.extend(old_ips)
        all_ips[province_isp] = list(set(ip_list))

    # ---- Step3: 检测 ----
    valid_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for province_isp, ip_list in all_ips.items():
            for ip in ip_list:
                futures.append(executor.submit(detect_ip, (ip, province_isp[:-2], province_isp[-2:])))
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                valid_results.append(res)

    # ---- Step4: 写回 ----
    valid_dict = {}
    for province_isp, ip_port in valid_results:
        if province_isp not in valid_dict:
            valid_dict[province_isp] = []
        valid_dict[province_isp].append(ip_port)

    for province_isp, ip_ports in valid_dict.items():
        with open(os.path.join(IP_FOLDER, f"{province_isp}.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(set(ip_ports))) + "\n")

    print("✅ 第一阶段完成，ip/*.txt 更新完毕\n")

# ========== 第二阶段 ==========
def stage_two():
    """每12轮触发：生成 URL 原始集合（不检测）"""
    print("🚀 第二阶段：生成 URL 列表中...")
    urls = []
    for file in os.listdir(IP_FOLDER):
        if file.endswith(".txt"):
            province_isp = file.replace(".txt", "")
            with open(os.path.join(IP_FOLDER, file), "r", encoding="utf-8") as f:
                for line in f:
                    ip_port = line.strip()
                    if ip_port:
                        urls.append((province_isp, ip_port))
    return urls

# ========== 第三阶段 ==========
def stage_three(urls):
    """生成 IPTV.txt"""
    print("🧩 第三阶段：生成 IPTV.txt...")
    seen = set()
    output_lines = []
    for province_isp, ip_port in urls:
        if ip_port not in seen:
            seen.add(ip_port)
            output_lines.append(f"{province_isp},{ip_port}")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
    print("🎉 IPTV.txt 已生成\n")

# ========== 主流程 ==========
def main():
    # 模拟计数
    count = 0
    if os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, "r", encoding="utf-8") as f:
            count = int(f.read().strip() or 0)
    count += 1
    with open(COUNTER_FILE, "w", encoding="utf-8") as f:
        f.write(str(count))

    print(f"===== 当前轮次：{count} =====\n")

    # 模拟抓到的新IP
    new_ips = ["36.158.22.13", "223.104.55.78", "117.136.12.45", "110.52.88.22"]

    # 阶段1
    stage_one(new_ips)

    # 每12轮触发阶段2、3
    if count % 12 == 0:
        urls = stage_two()
        stage_three(urls)
        print("🚀 本轮触发第二、三阶段\n")

    print("任务完成 ✅")

if __name__ == "__main__":
    main()