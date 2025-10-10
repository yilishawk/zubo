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
# ===============================
# 第二阶段：生成原始 zubo.txt（不推送）
if run_count in [12, 24, 36, 48, 60, 72]:
    print(f"🔔 第二阶段触发：生成 zubo.txt（第 {run_count} 次）")
    combined_lines = []

    # 遍历 ip/ 文件夹
    for ip_file in os.listdir(IP_DIR):
        if not ip_file.endswith(".txt"):
            continue
        ip_path = os.path.join(IP_DIR, ip_file)
        rtp_path = os.path.join(RTP_DIR, ip_file)
        if not os.path.exists(rtp_path):
            continue

        province_operator = ip_file.replace(".txt", "")  # 省份+运营商名
        with open(ip_path, "r", encoding="utf-8") as f_ip, \
             open(rtp_path, "r", encoding="utf-8") as f_rtp:
            ip_lines = [line.strip() for line in f_ip if line.strip()]
            rtp_lines = [line.strip() for line in f_rtp if line.strip()]

        if not ip_lines or not rtp_lines:
            continue

        first_rtp_line = rtp_lines[0]
        channel_name, rtp_url = first_rtp_line.split(",", 1)

        # 多线程检测
        def build_and_check(ip_port):
            try:
                url = f"http://{ip_port}/rtp/{rtp_url.split('rtp://')[1]}"
                resp = requests.get(url, timeout=5, stream=True)
                if resp.status_code == 200:
                    return f"{channel_name},{url}"
            except Exception:
                pass
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(build_and_check, ip_lines))

        # 保存有效 URL，并添加省份标识
        valid_urls = [r for r in results if r]
        for idx, res in enumerate(valid_urls, start=1):
            suffix = f"${province_operator}{idx if len(valid_urls) > 1 else ''}"
            combined_lines.append(f"{res}{suffix}")

        # 其余 rtp_lines 不检测，直接组合
        for ip_port in ip_lines:
            for other_rtp_line in rtp_lines[1:]:
                ch_name, rtp_url_rest = other_rtp_line.split(",", 1)
                combined_lines.append(f"{ch_name},http://{ip_port}/rtp/{rtp_url_rest.split('rtp://')[1]}${province_operator}")

    # 去重（按 URL 部分）
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

    print(f"🎯 第二阶段完成，已生成原始 {ZUBO_FILE}，共 {len(combined_lines)} 条 URL")

# ===============================
# 第三阶段：处理 zubo.txt（CCTV1检测+映射+分类+推送）
if run_count in [12, 24, 36, 48, 60, 72]:
    print(f"🔔 第三阶段开始处理 zubo.txt（第 {run_count} 次）")
    
    # 读取 zubo.txt
    zubo_lines = []
    with open(ZUBO_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                zubo_lines.append(line)

    # 按 IP 分组
    ip_group = {}
    for line in zubo_lines:
        channel, url_suffix = line.split(",", 1)
        ip = re.search(r"http://([^/]+)/", url_suffix).group(1)
        if ip not in ip_group:
            ip_group[ip] = []
        ip_group[ip].append((channel, url_suffix))

    # CCTV1 播放检测，只保留能用的 IP 的所有频道
    valid_lines = []
    for ip, items in ip_group.items():
        cctv1_urls = [url for ch, url in items if "CCTV1" in ch]
        success = False
        for test_url in cctv1_urls:
            try:
                resp = requests.get(test_url.split("$")[0], timeout=5, stream=True)
                if resp.status_code == 200:
                    success = True
                    break
            except Exception:
                continue
        if success:
            valid_lines.extend(items)

    # ===== 频道映射到标准名 =====
    CHANNEL_MAPPING = {
        # （完整映射，保持你之前提供的 CHANNEL_MAPPING）
        "CCTV1": ["CCTV-1", "CCTV-1 HD", "CCTV1 HD", "CCTV-1综合", "CCTV1 4M1080", "CCTV1 5M1080HEVC"],
        "CCTV2": ["CCTV-2", "CCTV-2 HD", "CCTV2 HD", "CCTV-2财经", "CCTV2 720", "节目暂时不可用 1080"],
        "CCTV3": ["CCTV-3", "CCTV-3 HD", "CCTV3 HD", "CCTV-3综艺", "CCTV3 4M1080"],
        "CCTV4": ["CCTV-4", "CCTV-4 HD", "CCTV4 HD", "CCTV4a", "CCTV4A", "CCTV-4中文国际", "CCTV4 4M1080"],
        "CCTV4欧洲": ["CCTV-4欧洲", "CCTV4欧洲 HD", "CCTV-4 欧洲", "CCTV4o", "CCTV4O", "CCTV-4中文国际欧洲", "CCTV4中文欧洲"],
        "CCTV4美洲": ["CCTV-4美洲", "CCTV-4北美", "CCTV4美洲 HD", "CCTV-4 美洲", "CCTV4m", "CCTV4M", "CCTV-4中文国际美洲", "CCTV4中文美洲"],
        "CCTV5": ["CCTV-5", "CCTV-5 HD", "CCTV5 HD", "CCTV-5体育", "CCTV5 4M1080"],
        "CCTV5+": ["CCTV-5+", "CCTV-5+ HD", "CCTV5+ HD", "CCTV-5+体育赛事", "CCTV5+ 4M1080"],
        "CCTV6": ["CCTV-6", "CCTV-6 HD", "CCTV6 HD", "CCTV-6电影", "CCTV6 4M1080"],
        "CCTV7": ["CCTV-7", "CCTV-7 HD", "CCTV7 HD", "CCTV-7国防军事", "CCTV7 4M1080"],
        "CCTV8": ["CCTV-8", "CCTV-8 HD", "CCTV8 HD", "CCTV-8电视剧", "CCTV8 4M1080"],
        "CCTV9": ["CCTV-9", "CCTV-9 HD", "CCTV9 HD", "CCTV-9纪录", "CCTV9 4M1080"],
        "CCTV10": ["CCTV-10", "CCTV-10 HD", "CCTV10 HD", "CCTV-10科教", "CCTV10 4M1080", "CCTV10 5M1080HEVC"],
        "CCTV11": ["CCTV-11", "CCTV-11 HD", "CCTV11 HD", "CCTV-11戏曲", "CCTV11 5M1080HEVC"],
        "CCTV12": ["CCTV-12", "CCTV-12 HD", "CCTV12 HD", "CCTV-12社会与法", "CCTV12 4M1080", "CCTV12 5M1080HEVC"],
        "CCTV13": ["CCTV-13", "CCTV-13 HD", "CCTV13 HD", "CCTV-13新闻", "CCTV13 5M1080HEVC", "CCTV13 4M1080"],
        "CCTV14": ["CCTV-14", "CCTV-14 HD", "CCTV14 HD", "CCTV-14少儿", "CCTV14 4M1080", "CCTV14 5M1080HEVC"],
        "CCTV15": ["CCTV-15", "CCTV-15 HD", "CCTV15 HD", "CCTV-15音乐", "CCTV15 5M1080HEVC"],
        "CCTV16": ["CCTV-16", "CCTV-16 HD", "CCTV-16 4K", "CCTV-16奥林匹克", "CCTV16 4K", "CCTV-16奥林匹克4K", "CCTV16 4M1080"],
        "CCTV17": ["CCTV-17", "CCTV-17 HD", "CCTV17 HD", "CCTV-17农业农村", "CCTV17 4M1080"],
        # （其他频道映射略，为完整可直接拷贝你之前的映射）
    }

    def map_channel(ch):
        for std_name, aliases in CHANNEL_MAPPING.items():
            if ch in aliases or ch == std_name:
                return std_name
        return ch

    mapped_lines = []
    for ch, url in valid_lines:
        std_ch = map_channel(ch)
        mapped_lines.append(f"{std_ch},{url}")

    # ===== 分类排序 =====
    CHANNEL_CATEGORIES = {
        # （完整分类，保持你提供的 CHANNEL_CATEGORIES）
        "央视频道": [
            "CCTV1", "CCTV2", "CCTV3", "CCTV4", "CCTV4欧洲", "CCTV4美洲", "CCTV5", "CCTV5+", "CCTV6", "CCTV7",
            "CCTV8", "CCTV9", "CCTV10", "CCTV11", "CCTV12", "CCTV13", "CCTV14", "CCTV15", "CCTV16", "CCTV17", "CCTV4K", "CCTV8K",
            "兵器科技", "风云音乐", "风云足球", "风云剧场", "怀旧剧场", "第一剧场", "女性时尚", "世界地理", "央视台球", "高尔夫网球",
            "央视文化精品", "卫生健康", "电视指南"
        ],
        "卫视频道": [
            "湖南卫视", "浙江卫视", "江苏卫视", "东方卫视", "深圳卫视", "北京卫视", "广东卫视", "广西卫视", "东南卫视", "海南卫视",
            "河北卫视", "河南卫视", "湖北卫视", "江西卫视", "四川卫视", "重庆卫视", "贵州卫视", "云南卫视", "天津卫视", "安徽卫视",
            "山东卫视", "辽宁卫视", "黑龙江卫视", "吉林卫视", "内蒙古卫视", "宁夏卫视", "山西卫视", "陕西卫视", "甘肃卫视", "青海卫视",
            "新疆卫视", "西藏卫视", "三沙卫视", "兵团卫视", "延边卫视", "安多卫视", "康巴卫视", "农林卫视", "山东教育卫视",
            "中国教育1台", "中国教育2台", "中国教育3台", "中国教育4台", "早期教育"
        ],
        "数字频道": [
            "CHC动作电影", "CHC家庭影院", "CHC影迷电影", "淘电影", "淘精彩", "淘剧场", "淘4K", "淘娱乐", "淘BABY", "淘萌宝",
            "淘小剧场", "淘趣味", "淘亲子", "淘电影4K"
        ],
        # 其他分类略，可按你原来 CHANNEL_CATEGORIES 填写
    }

    sorted_lines = []
    for category, channels in CHANNEL_CATEGORIES.items():
        for ch in channels:
            for line in mapped_lines:
                line_ch, url = line.split(",", 1)
                if line_ch == ch:
                    sorted_lines.append(line)

    # 写入 zubo.txt 并推送
    with open(ZUBO_FILE, "w", encoding="utf-8") as f:
        for line in sorted_lines:
            f.write(line + "\n")

    print(f"🎯 第三阶段完成，最终 zubo.txt 共 {len(sorted_lines)} 条可用 URL，开始推送到仓库...")

    # 推送
    os.system('git config --global user.name "github-actions"')
    os.system('git config --global user.email "github-actions@users.noreply.github.com"')
    os.system("git add zubo.txt")
    os.system(f'git commit -m "自动更新 zubo.txt（第 {run_count} 次）" || echo "⚠️ 无需提交"')
    os.system("git push origin main")