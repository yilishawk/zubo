import os
import re
import requests
import json
import time
import concurrent.futures
import subprocess
from datetime import datetime, timezone, timedelta
import random
import logging

# ===============================
# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("new_iptv.log")  # 新日志文件
    ]
)

# ===============================
# 配置区
FOFA_URL = "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyI="
HEADERS = [
"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
]
COUNTER_FILE = "new_计数.txt"  # 新计数文件
IP_DIR = "new_ip"  # 新 IP 目录
IPTV_FILE = "New_IPTV.txt"  # 新 IPTV 文件

# 频道分类
CHANNEL_CATEGORIES = {
    "央视频道": [
        "CCTV1", "CCTV2", "CCTV3", "CCTV4", "CCTV5", "CCTV6", "CCTV7",
        "CCTV8", "CCTV9", "CCTV10", "CCTV11", "CCTV12", "CCTV13", "CCTV14", "CCTV15"
    ],
    "卫视频道": [
        "湖南卫视", "浙江卫视", "江苏卫视", "东方卫视", "深圳卫视", "北京卫视", "广东卫视",
        "陕西卫视", "安徽卫视", "四川卫视", "重庆卫视", "东南卫视", "河南卫视", "山西卫视", 
        "江西卫视", "贵州卫视"
    ],
    "香港电视": ["凤凰卫视"],
    "省内": ["陕西一套", "陕西二套"],
}

# 频道映射
CHANNEL_MAPPING = {
    "CCTV1": ["CCTV1-综合", "CCTV-1", "CCTV1 HD"],
    "CCTV2": ["CCTV2-财经", "CCTV-2", "CCTV2 HD"],
    "CCTV3": ["CCTV3-综艺", "CCTV-3", "CCTV3 HD"],
    "CCTV4": ["CCTV4-国际", "CCTV-4", "CCTV4 HD"],
    "CCTV5": ["CCTV5-体育", "CCTV-5", "CCTV5 HD"],
    "CCTV6": ["CCTV6-电影", "CCTV-6", "CCTV6 HD"],
    "CCTV7": ["CCTV7-军农", "CCTV-7", "CCTV7 HD"],
    "CCTV8": ["CCTV8-电视剧", "CCTV-8", "CCTV8 HD"],
    "CCTV9": ["CCTV9-纪录", "CCTV-9", "CCTV9 HD"],
    "CCTV10": ["CCTV10-科教", "CCTV-10", "CCTV10 HD"],
    "CCTV11": ["CCTV11-戏曲", "CCTV-11", "CCTV11 HD"],
    "CCTV12": ["CCTV12-社会与法", "CCTV-12", "CCTV12 HD"],
    "CCTV13": ["CCTV13-新闻", "CCTV-13", "CCTV13 HD"],
    "CCTV14": ["CCTV14-少儿", "CCTV-14", "CCTV14 HD"],
    "CCTV15": ["CCTV15-音乐", "CCTV-15", "CCTV15 HD"],
    "湖南卫视": ["湖南卫视HD", "湖南卫视"],
    "浙江卫视": ["浙江卫视HD", "浙江卫视"],
    "江苏卫视": ["江苏卫视HD", "江苏卫视"],
    "东方卫视": ["上海卫视", "东方卫视"],
    "深圳卫视": ["深圳卫视HD", "深圳卫视"],
    "北京卫视": ["北京卫视HD", "北京卫视"],
    "广东卫视": ["广东卫视HD", "广东卫视"],
    "陕西卫视": ["陕西卫视", "陕西卫视HD"],
    "安徽卫视": ["安徽卫视HD", "安徽卫视"],
    "四川卫视": ["四川卫视", "四川卫视HD"],
    "重庆卫视": ["重庆卫视", "重庆卫视HD"],
    "东南卫视": ["东南卫视"],
    "河南卫视": ["河南卫视", "河南卫视HD"],
    "山西卫视": ["山西卫视"],
    "江西卫视": ["江西卫视"],
    "贵州卫视": ["贵州卫视"],
    "凤凰卫视": ["凤凰卫视"],
    "陕西一套": ["陕西一套"],
    "陕西二套": ["陕西二套"],
}

# ===============================
# 计数逻辑
def get_run_count():
    if os.path.exists(COUNTER_FILE):
        try:
            return int(open(COUNTER_FILE).read().strip())
        except Exception as e:
            logging.error(f"读取计数文件失败：{e}")
            return 0
    return 0

def save_run_count(count):
    try:
        open(COUNTER_FILE, "w").write(str(count))
        logging.info(f"保存计数：{count}")
    except Exception as e:
        logging.error(f"保存计数文件失败：{e}")

def check_and_clear_files_by_run_count():
    os.makedirs(IP_DIR, exist_ok=True)
    count = get_run_count() + 1
    if count >= 73:
        logging.info(f"🧹 第 {count} 次运行，清空 {IP_DIR} 下所有 .txt 文件")
        for f in os.listdir(IP_DIR):
            if f.endswith(".txt"):
                try:
                    os.remove(os.path.join(IP_DIR, f))
                except Exception as e:
                    logging.error(f"删除 {f} 失败：{e}")
        save_run_count(1)
        return "w", 1
    else:
        save_run_count(count)
        return "a", count

# ===============================
# IP 运营商判断
def get_isp(ip):
    if re.match(r"^(1[0-9]{2}|2[0-3]{2}|42|43|58|59|60|61|110|111|112|113|114|115|116|117|118|119|120|121|122|123|124|125|126|127|175|180|182|183|184|185|186|187|188|189|223)\.", ip):
        return "电信"
    elif re.match(r"^(42|43|58|59|60|61|110|111|112|113|114|115|116|117|118|119|120|121|122|123|124|125|126|127|175|180|182|183|184|185|186|187|188|189|223)\.", ip):
        return "联通"
    elif re.match(r"^(223|36|37|38|39|100|101|102|103|104|105|106|107|108|109|134|135|136|137|138|139|150|151|152|157|158|159|170|178|182|183|184|187|188|189)\.", ip):
        return "移动"
    else:
        return "未知"

# ===============================
# 检查 FFmpeg 可用性
def check_ffmpeg():
    try:
        subprocess.run(["ffprobe", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        logging.info("✅ FFmpeg 已安装")
        return True
    except Exception as e:
        logging.error(f"❌ FFmpeg 未安装或不可用：{e}")
        return False

# ===============================
# 第一阶段：从 FOFA 爬取 IP:PORT
def first_stage():
    all_ips = set()
    logging.info(f"📡 正在爬取 FOFA URL: {FOFA_URL}")
    for header in HEADERS:
        try:
            r = requests.get(FOFA_URL, headers=header, timeout=15)
            ips_found = re.findall(r'http://([\d\.]+:\d+)/?', r.text)
            all_ips.update(ips_found)
            logging.info(f"✅ 从本次请求提取 {len(ips_found)} 个 IP:PORT")
        except Exception as e:
            logging.error(f"❌ 爬取失败：{e}")
        time.sleep(random.uniform(1, 3))

    if not all_ips:
        logging.warning("⚠️ 未找到 IP，可能是 FOFA 反爬或结果为空")
        return 0

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
            time.sleep(0.5)
        except Exception as e:
            logging.error(f"❌ 查询 {ip_port} 的地区失败：{e}")
            continue

    mode, run_count = check_and_clear_files_by_run_count()
    for filename, ip_set in province_isp_dict.items():
        path = os.path.join(IP_DIR, filename)
        try:
            with open(path, mode, encoding="utf-8") as f:
                for ip_port in sorted(ip_set):
                    f.write(ip_port + "\n")
            logging.info(f"{path} 已{'覆盖' if mode=='w' else '追加'}写入 {len(ip_set)} 个 IP")
        except Exception as e:
            logging.error(f"❌ 写入 {path} 失败：{e}")
    logging.info(f"✅ 第一阶段完成，当前轮次：{run_count}")
    return run_count

# ===============================
# 第二/第三阶段合并：获取 JSON、处理 URL、测试连通性、生成 IPTV
def generate_iptv():
    if not check_ffmpeg():
        logging.error("⚠️ FFmpeg 不可用，跳过 IPTV 生成")
        return

    logging.info("🔔 生成 IPTV：遍历 IP 获取 JSON 并测试")
    if not os.path.exists(IP_DIR):
        logging.error("⚠️ new_ip 目录不存在")
        return

    alias_map = {}
    for main_name, aliases in CHANNEL_MAPPING.items():
        for alias in aliases:
            alias_map[alias] = main_name

    ip_info = {}
    for fname in os.listdir(IP_DIR):
        if not fname.endswith(".txt"):
            continue
        province_operator = fname.replace(".txt", "")
        path = os.path.join(IP_DIR, fname)
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    ip_port = line.strip()
                    ip_info[ip_port] = province_operator
        except Exception as e:
            logging.error(f"❌ 读取 {path} 失败：{e}")
            continue

    all_valid_lines = []
    seen = set()

    def process_ip(ip_port):
        base_url = f"http://{ip_port}"
        json_url = f"{base_url}/iptv/live/1000.json?key=txiptv"
        try:
            r = requests.get(json_url, timeout=10)
            if r.status_code != 200:
                logging.warning(f"⚠️ {json_url} 返回状态码 {r.status_code}")
                return []
            data = r.json()
            if data.get("code") != 0 or not data.get("data"):
                logging.warning(f"⚠️ {json_url} 返回无效数据")
                return []

            local_valid = []
            for item in data["data"]:
                ch_name = item.get("name", "")
                rel_url = item.get("url", "")
                if not ch_name or not rel_url:
                    continue

                if rel_url.startswith("http://"):
                    parsed = re.sub(r'http://[^/]+', base_url, rel_url)
                else:
                    parsed = f"{base_url}{rel_url}"

                ch_main = alias_map.get(ch_name, ch_name)
                key = f"{ch_main},{parsed}"
                if key in seen:
                    continue
                seen.add(key)

                if "CCTV1" in ch_name or not local_valid:
                    if check_m3u8(parsed):
                        local_valid.append(f"{ch_main},{parsed}${ip_info.get(ip_port, '未知')}")
            return local_valid
        except Exception as e:
            logging.error(f"❌ 处理 {ip_port} 失败：{e}")
            return []

    def check_m3u8(url, timeout=5):
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_streams", "-i", url],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout + 2
            )
            return b"codec_type" in result.stdout
        except Exception as e:
            logging.error(f"❌ 检查 {url} 失败：{e}")
            return False

    ip_ports = list(ip_info.keys())
    logging.info(f"🚀 多线程处理 {len(ip_ports)} 个 IP")
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_ip, ip) for ip in ip_ports]
        for future in concurrent.futures.as_completed(futures):
            all_valid_lines.extend(future.result())

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
                    for line in all_valid_lines:
                        name = line.split(",", 1)[0]
                        if name == ch:
                            f.write(line + "\n")
                f.write("\n")
        logging.info(f"🎯 {IPTV_FILE} 生成完成，共 {len(all_valid_lines)} 条有效频道")
    except Exception as e:
        logging.error(f"❌ 写入 {IPTV_FILE} 失败：{e}")

# ===============================
# 文件推送
def push_all_files():
    logging.info("🚀 推送所有更新文件到 GitHub...")
    try:
        os.system('git config --global user.name "github-actions[bot]"')
        os.system('git config --global user.email "github-actions[bot]@users.noreply.github.com"')
        os.system(f"git add {COUNTER_FILE}")
        os.system(f"git add {IP_DIR}/*.txt || true")
        os.system(f"git add {IPTV_FILE} || true")
        os.system("git add new_iptv.log || true")
        os.system('git commit -m "自动更新：新计数、新IP文件、New_IPTV.txt、日志" || echo "⚠️ 无需提交"')
        os.system("git push origin main")
        logging.info("✅ 文件推送成功")
    except Exception as e:
        logging.error(f"❌ 推送失败：{e}")

# ===============================
# 主执行逻辑
if __name__ == "__main__":
    run_count = first_stage()
    if run_count in [2, 4, 6]:
        generate_iptv()
    push_all_files()
