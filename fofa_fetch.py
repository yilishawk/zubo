import os
import re
import requests
import time
from datetime import datetime
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
    每运行19次清空 IP_DIR 下所有 txt 文件。
    前18次追加，第19次清空覆盖。
    返回写入模式 w 或 a
    """
    os.makedirs(IP_DIR, exist_ok=True)
    count = get_run_count() + 1
    if count >= 19:
        print(f"🧹 第 {count} 次运行，清空 {IP_DIR} 下所有 .txt 文件...")
        for file in os.listdir(IP_DIR):
            if file.endswith(".txt"):
                os.remove(os.path.join(IP_DIR, file))
                print(f"已删除：{file}")
        save_run_count(1)  # 清空后计数从1开始
        return "w", 1
    else:
        print(f"⏰ 当前第 {count} 次运行，本次执行为追加模式")
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
        if fname not in province_isp_dict:
            province_isp_dict[fname] = set()
        province_isp_dict[fname].add(ip_port)
        time.sleep(0.5)
    except Exception as e:
        print(f"{ip_port} 查询失败：{e}")
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
# -------------------------------
# 第二阶段：按新规则触发并生成 zubo.txt
# 触发：run_count 为 12、24、36、48、60、72 时执行生成
# 额外：当 run_count == 73 时，清空 ip/ 下所有 txt 并将计数重置为 1（开始新轮回）
# 注意：本段只负责生成 zubo.txt（覆盖），不负责 git 提交/推送
# -------------------------------

# 需要 concurrent.futures 已在文件顶部导入
import concurrent.futures

# 触发集合（12 的倍数，到 72）
TRIGGERS = {12, 24, 36, 48, 60, 72}

if run_count in TRIGGERS:
    print(f"🔔 第二阶段触发（run_count={run_count}）：生成 {ZUBO_FILE}")
    combined_lines = []

    # 遍历 ip/ 文件夹中每个 txt 文件
    for ip_file in os.listdir(IP_DIR):
        if not ip_file.endswith(".txt"):
            continue

        ip_path = os.path.join(IP_DIR, ip_file)
        rtp_path = os.path.join(RTP_DIR, ip_file)
        if not os.path.exists(rtp_path):
            # 没有同名 rtp 文件则跳过
            continue

        provider_name = ip_file.replace(".txt", "")  # 用于后缀，如 "广东电信"

        # 读取 ip 与 rtp 文件内容
        with open(ip_path, "r", encoding="utf-8") as f_ip:
            ip_lines = [line.strip() for line in f_ip if line.strip()]
        with open(rtp_path, "r", encoding="utf-8") as f_rtp:
            rtp_lines = [line.strip() for line in f_rtp if line.strip()]

        if not ip_lines or not rtp_lines:
            continue  # 内容为空则跳过

        # 只检测 rtp 文件的第一行（保持原有逻辑）
        first_rtp_line = rtp_lines[0]
        try:
            first_channel_name, first_rtp_url = first_rtp_line.split(",", 1)
        except Exception:
            # 格式异常，跳过该文件
            print(f"⚠️ 跳过（格式异常）：{rtp_path}")
            continue

        # 仅支持标准 rtp:// 格式（符合你之前的要求）
        if "rtp://" not in first_rtp_url:
            print(f"⚠️ 跳过（非标准 rtp://）：{first_rtp_url}")
            continue
        first_rtp_part = first_rtp_url.split("rtp://", 1)[1]

        # -------------------
        # 多线程检测（只检测第一行）：
        # 返回通过检测（HTTP 200）的 ip_port 列表（保持顺序并去重）
        def check_ip_for_first_rtp(ip_port):
            try:
                url = f"http://{ip_port}/rtp/{first_rtp_part}"
                resp = requests.get(url, timeout=5, stream=True)
                if resp.status_code == 200:
                    return ip_port
            except Exception:
                return None
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(check_ip_for_first_rtp, ip_lines))

        # 保留检测成功且去重的 ip 顺序
        valid_ips = []
        for r in results:
            if r and r not in valid_ips:
                valid_ips.append(r)

        if not valid_ips:
            # 该 provider 没有可用 IP，跳过
            print(f"❌ {provider_name} 无可用 IP，跳过")
            continue

        # 为每个通过检测的 IP 分配后缀（若只有 1 个则不编号；若多个则编号从1开始）
        suffix_map = {}
        if len(valid_ips) == 1:
            suffix_map[valid_ips[0]] = f"${provider_name}"
        else:
            for idx, ip_val in enumerate(valid_ips, start=1):
                suffix_map[ip_val] = f"${provider_name}{idx}"

        # 使用通过检测的 IP 去合并 rtp_lines（包括第一行与其他行）
        for ip_port in valid_ips:
            suffix = suffix_map[ip_port]
            for rtp_line in rtp_lines:
                try:
                    ch_name, rtp_url_line = rtp_line.split(",", 1)
                except Exception:
                    continue
                # 仅支持标准 rtp://，其余格式跳过
                if "rtp://" not in rtp_url_line:
                    continue
                rtp_part_line = rtp_url_line.split("rtp://", 1)[1]
                merged_url = f"http://{ip_port}/rtp/{rtp_part_line}"
                combined_lines.append(f"{ch_name},{merged_url}{suffix}")

    # 全局去重（保留原顺序）
    combined_lines = list(dict.fromkeys(combined_lines))

    # 写入 zubo.txt（覆盖）
    with open(ZUBO_FILE, "w", encoding="utf-8") as f:
        for line in combined_lines:
            f.write(line + "\n")

    print(f"🎯 第二阶段完成，已生成 {ZUBO_FILE}，共 {len(combined_lines)} 条唯一 URL")

# -------------------------------
# 第73次：清空 ip/ 下所有 txt 并把计数重置为 1（开始新轮回）
# 注意：这个分支与第二阶段并列，当 run_count == 73 时会运行
if run_count == 73:
    print("🧹 run_count == 73，开始清空 ip/ 下所有 .txt 并重置计数为 1")
    try:
        for file in os.listdir(IP_DIR):
            if file.endswith(".txt"):
                os.remove(os.path.join(IP_DIR, file))
                print(f"已删除：{file}")
        # 将计数写为 1，开始新轮回
        save_run_count(1)
        print("✅ 清空完成，计数已重置为 1")
    except Exception as e:
        print(f"清空 ip/ 时发生错误：{e}")