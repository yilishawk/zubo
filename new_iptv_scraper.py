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
        logging.FileHandler("new_iptv.log", encoding='utf-8')
    ]
)

# ===============================
# 配置区
FOFA_URL = "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyI="
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
COUNTER_FILE = "new_计数.txt"
IP_DIR = "new_ip"
IPTV_FILE = "New_IPTV.txt"

# ===============================
# 【完整频道映射】40频道全覆盖
FULL_CHANNEL_MAPPING = {
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
    "山西卫视": ["山西卫视"],
    "湖南卫视": ["湖南卫视"],
    "浙江卫视": ["浙江卫视"],
    "广东卫视": ["广东卫视"],
    "深圳卫视": ["深圳卫视"],
    "天津卫视": ["天津卫视"],
    "山东卫视": ["山东卫视"],
    "重庆卫视": ["重庆卫视"],
    "金鹰卡通": ["金鹰卡通"],
    "湖北卫视": ["湖北卫视"],
    "黑龙江卫视": ["黑龙江卫视"],
    "辽宁卫视": ["辽宁卫视"],
    "上海卫视": ["上海卫视", "东方卫视"],
    "江苏卫视": ["江苏卫视"],
    "北京卫视": ["北京卫视"],
    "四川卫视": ["四川卫视"],
    "河南卫视": ["河南卫视"],
    "贵州卫视": ["贵州卫视"],
    "东南卫视": ["东南卫视"],
    "广西卫视": ["广西卫视"],
    "江西卫视": ["江西卫视"],
    "吉林卫视": ["吉林卫视"],
    "青海卫视": ["青海卫视"],
    "安徽卫视": ["安徽卫视"],
    "陕西卫视": ["陕西卫视"],
    "凤凰卫视": ["凤凰卫视"],
}

# 频道分类
CHANNEL_CATEGORIES = {
    "央视频道": [k for k in FULL_CHANNEL_MAPPING.keys() if k.startswith("CCTV")],
    "卫视频道": [k for k in FULL_CHANNEL_MAPPING.keys() if "卫视" in k and k not in ["凤凰卫视"]],
    "香港电视": ["凤凰卫视"],
    "少儿频道": ["金鹰卡通"],
}

# ===============================
# 计数逻辑
def get_run_count():
    if os.path.exists(COUNTER_FILE):
        try:
            return int(open(COUNTER_FILE, encoding='utf-8').read().strip())
        except:
            return 0
    return 0

def save_run_count(count):
    try:
        with open(COUNTER_FILE, "w", encoding='utf-8') as f:
            f.write(str(count))
        logging.info(f"✅ 保存计数：{count}")
    except Exception as e:
        logging.error(f"❌ 保存计数失败：{e}")

def check_and_clear_files_by_run_count():
    os.makedirs(IP_DIR, exist_ok=True)
    count = get_run_count() + 1
    mode = "w" if count >= 73 else "a"
    if count >= 73:
        logging.info(f"🧹 第 {count} 次运行，清空IP目录")
        for f in os.listdir(IP_DIR):
            if f.endswith(".txt"):
                try:
                    os.remove(os.path.join(IP_DIR, f))
                except:
                    pass
        count = 1
    save_run_count(count)
    return mode, count

# ===============================
# IP运营商判断（简化版）
def get_isp(ip):
    ip_prefix = ip.split('.')[0]
    if ip_prefix in ['111', '112', '113', '114', '115', '116', '117', '118', '119', '120', '121', '122', '123', '124', '125', '126', '127']:
        return "电信"
    elif ip_prefix in ['42', '43', '101', '103', '106', '110', '175', '180', '182', '183', '185', '186', '187']:
        return "联通"
    elif ip_prefix in ['223', '36', '37', '38', '39', '100', '134', '135', '136', '137', '138', '139', '150', '151', '152', '157', '158', '159', '170', '178', '184']:
        return "移动"
    return "其他"

# ===============================
# FFmpeg检查
def check_ffmpeg():
    try:
        subprocess.run(["ffprobe", "-version"], stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE, check=True, timeout=5)
        return True
    except:
        return False

# ===============================
# 第一阶段：抓取IP
def first_stage():
    mode, run_count = check_and_clear_files_by_run_count()
    
    logging.info(f"📡 爬取FOFA：{FOFA_URL}")
    
    try:
        time.sleep(random.uniform(1, 3))
        response = requests.get(FOFA_URL, headers=HEADERS, timeout=20)
        response.raise_for_status()
        
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}:[0-9]{2,5}\b'
        all_ips = set(re.findall(ip_pattern, response.text))
        
        logging.info(f"✅ 提取 {len(all_ips)} 个唯一IP")
        
        if not all_ips:
            return run_count

        # 查询地区并保存
        province_isp_dict = {}
        with requests.Session() as session:
            session.headers.update(HEADERS)
            for ip_port in all_ips:
                ip = ip_port.split(':')[0]
                try:
                    resp = session.get(f"http://ip-api.com/json/{ip}?lang=zh-CN", timeout=8)
                    data = resp.json()
                    if data.get("status") == "success":
                        province = data.get("regionName", "未知")
                        isp = get_isp(ip)
                        if isp != "其他":
                            location = f"{province}{isp}"
                            province_isp_dict.setdefault(location, set()).add(ip_port)
                except:
                    continue
                time.sleep(0.5)

        # 保存文件
        for filename, ip_set in province_isp_dict.items():
            path = os.path.join(IP_DIR, f"{filename}.txt")
            with open(path, mode, encoding="utf-8") as f:
                for ip_port in sorted(ip_set):
                    f.write(ip_port + "\n")
            logging.info(f"💾 {path}：{len(ip_set)}个IP")

    except Exception as e:
        logging.error(f"❌ 第一阶段失败：{e}")
    
    logging.info(f"✅ 第一阶段完成，轮次：{run_count}")
    return run_count

# ===============================
# 第二阶段：终极版IPTV生成（一IP通吃40频道）
def generate_iptv():
    if not check_ffmpeg():
        logging.error("⚠️ FFmpeg不可用，跳过IPTV生成")
        return

    logging.info("🎬 【终极版】一IP通吃40频道策略")
    
    # 构建别名映射
    alias_map = {}
    for main_name, aliases in FULL_CHANNEL_MAPPING.items():
        for alias in aliases:
            alias_map[alias] = main_name

    # 读取IP信息
    ip_info = {}
    for fname in os.listdir(IP_DIR):
        if fname.endswith(".txt"):
            province_operator = fname.replace(".txt", "")
            with open(os.path.join(IP_DIR, fname), encoding="utf-8") as f:
                for line in f:
                    ip_port = line.strip()
                    if ip_port:
                        ip_info[ip_port] = province_operator

    all_valid_lines = []
    seen_urls = set()

    def process_ip(ip_port):
        try:
            base_url = f"http://{ip_port}"
            json_url = f"{base_url}/iptv/live/1000.json?key=txiptv"
            
            resp = requests.get(json_url, timeout=8)
            if resp.status_code != 200:
                return []
                
            data = resp.json()
            if data.get("code") != 0 or not data.get("data"):
                return []

            # 只测试CCTV1验证IP
            test_url = None
            for item in data["data"]:
                if "CCTV1" in item.get("name", ""):
                    rel_url = item.get("url", "")
                    test_url = f"{base_url}{rel_url}" if not rel_url.startswith("http") else rel_url
                    break
            
            if not test_url:
                return []

            # 一IP通吃：CCTV1通过=40频道全通过！
            if check_m3u8_fast(test_url):
                logging.info(f"✅ {ip_port} CCTV1通过 → 40频道全采纳！")
                
                valid_channels = []
                for item in data["data"]:
                    ch_name = item.get("name", "")
                    rel_url = item.get("url", "")
                    
                    if not ch_name or not rel_url:
                        continue
                        
                    parsed_url = f"{base_url}{rel_url}" if not rel_url.startswith("http") else re.sub(r'http://[^/]+', base_url, rel_url)
                    
                    if parsed_url in seen_urls:
                        continue
                    seen_urls.add(parsed_url)
                    
                    ch_main = alias_map.get(ch_name, ch_name)
                    valid_channels.append(f"{ch_main},{parsed_url}${ip_info.get(ip_port, '未知')}")
                
                return valid_channels
            else:
                logging.debug(f"❌ {ip_port} CCTV1失败")
                return []

        except Exception as e:
            logging.debug(f"处理 {ip_port} 失败：{e}")
            return []

    def check_m3u8_fast(url, timeout=4):
        try:
            if requests.head(url, timeout=2).status_code == 200:
                return True
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-t", "2", "-i", url],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout
            )
            return result.returncode == 0
        except:
            return False

    # 多线程处理
    ip_ports = list(ip_info.keys())
    logging.info(f"🚀 测试 {len(ip_ports)} 个IP（每IP只测1个频道）")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_ip, ip) for ip in ip_ports]
        for future in concurrent.futures.as_completed(futures):
            all_valid_lines.extend(future.result())

    # 生成M3U文件
    beijing_now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with open(IPTV_FILE, "w", encoding="utf-8") as f:
            f.write(f"#EXTM3U\n")
            f.write(f'#PLAYLIST: {beijing_now} | 频道: {len(all_valid_lines)//len(ip_info)}x40 = {len(all_valid_lines)}\n\n')
            
            for category, ch_list in CHANNEL_CATEGORIES.items():
                f.write(f"#EXTINF:-1 group-title=\"{category}\"\n")
                category_lines = [line for line in all_valid_lines if line.split(",", 1)[0] in ch_list]
                for line in sorted(category_lines):
                    url_part = line.split("$")[0]
                    f.write(f"{url_part}\n")
                f.write("\n")

        total_channels = len(set(line.split(",", 1)[0] for line in all_valid_lines))
        logging.info(f"🎉 【终极成功】{IPTV_FILE} 生成完成！")
        logging.info(f"   📺 唯一频道: {total_channels}/40")
        logging.info(f"   🌐 有效源:   {len(all_valid_lines)}")
        
    except Exception as e:
        logging.error(f"❌ 写入失败：{e}")

# ===============================
# Git推送
def push_all_files():
    logging.info("📤 推送文件到GitHub")
    commands = [
        'git config --global user.name "github-actions[bot]"',
        'git config --global user.email "github-actions[bot]@users.noreply.github.com"',
        f'git add {COUNTER_FILE}',
        f'git add {IP_DIR}/*.txt || true',
        f'git add {IPTV_FILE} || true',
        'git add new_iptv.log || true',
        'git commit -m "🤖 自动更新IPTV源 $(date +%Y-%m-%d\ %H:%M)" || echo "无变化"',
        'git push origin main'
    ]
    
    for cmd in commands:
        result = os.system(cmd)
        if result != 0:
            logging.error(f"❌ 执行 {cmd} 失败")
            return False
    logging.info("✅ 推送成功")
    return True

# ===============================
# 【完整主程序入口】
if __name__ == "__main__":
    start_time = time.time()
    
    try:
        logging.info("🚀 【终极IPTV脚本】启动！")
        
        # 第一阶段：抓取IP
        run_count = first_stage()
        
        # 第二阶段：生成IPTV（第2,4,6次运行）
        if run_count in [2, 4, 6]:
            generate_iptv()
        
        # 第三阶段：推送GitHub
        push_all_files()
        
        elapsed = time.time() - start_time
        logging.info(f"✅ 任务完成！耗时：{elapsed:.1f}秒 | 轮次：{run_count}")
        
    except KeyboardInterrupt:
        logging.info("👋 用户中断")
    except Exception as e:
        logging.error(f"💥 程序异常：{e}")
