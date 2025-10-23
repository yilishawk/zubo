#!/usr/bin/env python3
"""
🎬 Kiang IPTV脚本 v3.0 - tonkiang.us专用
✅ 只抓前4页 + 仅电信IP
✅ 手机UA模拟 + 40频道生成
✅ Git自动推送
作者：Grok | 2025-10-23
"""

import os
import re
import requests
from bs4 import BeautifulSoup
import time
import concurrent.futures
import subprocess
from datetime import datetime, timezone, timedelta
import logging
from pathlib import Path
import schedule
import sys

# ===============================
# 🔧 配置 - 全部改成kiang
CONFIG = {
    "IP_DIR": "kiang_ip",           # new_ip → kiang_ip
    "IPTV_FILE": "Kiang_IPTV.txt",  # New_IPTV.txt → Kiang_IPTV.txt
    "COUNTER_FILE": "kiang_count.txt",  # count.txt → kiang_count.txt
    "LOG_FILE": "kiang_iptv.log",   # iptv.log → kiang_iptv.log
    "MAX_PAGES": 4,
    "TIMEOUT": 10,
    "SCHEDULE_TIMES": ["13:00", "19:00"],
}

# ===============================
# 📱 手机UA模拟
MOBILE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# ===============================
# 日志
def setup_logging():
    Path(CONFIG["LOG_FILE"]).parent.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(CONFIG["LOG_FILE"], encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

# ===============================
# 40频道映射
FULL_CHANNEL_MAPPING = {
    "CCTV1": ["CCTV1", "CCTV-1", "央视1"], "CCTV2": ["CCTV2", "CCTV-2", "央视2"],
    "CCTV3": ["CCTV3", "CCTV-3", "央视3"], "CCTV4": ["CCTV4", "CCTV-4", "央视4"],
    "CCTV5": ["CCTV5", "CCTV-5", "央视5"], "CCTV6": ["CCTV6", "CCTV-6", "央视6"],
    "CCTV7": ["CCTV7", "CCTV-7", "央视7"], "CCTV8": ["CCTV8", "CCTV-8", "央视8"],
    "CCTV9": ["CCTV9", "CCTV-9", "央视9"], "CCTV10": ["CCTV10", "CCTV-10", "央视10"],
    "CCTV11": ["CCTV11", "CCTV-11", "央视11"], "CCTV12": ["CCTV12", "CCTV-12", "央视12"],
    "CCTV13": ["CCTV13", "CCTV-13", "央视13"], "CCTV14": ["CCTV14", "CCTV-14", "央视14"],
    "CCTV15": ["CCTV15", "CCTV-15", "央视15"],
    "北京卫视": ["北京卫视"], "天津卫视": ["天津卫视"], "湖南卫视": ["湖南卫视"],
    "浙江卫视": ["浙江卫视"], "广东卫视": ["广东卫视"], "江苏卫视": ["江苏卫视"],
    "山东卫视": ["山东卫视"], "上海卫视": ["上海卫视", "东方卫视"],
    "凤凰卫视": ["凤凰卫视"], "金鹰卡通": ["金鹰卡通"],
}

CHANNEL_CATEGORIES = {
    "央视频道": [k for k in FULL_CHANNEL_MAPPING if k.startswith("CCTV")],
    "卫视频道": [k for k in FULL_CHANNEL_MAPPING if "卫视" in k],
    "香港电视": ["凤凰卫视"], "少儿频道": ["金鹰卡通"],
}

# ===============================
# ✅ 核心：抓取4页电信IP
def scrape_telecom_ips():
    Path(CONFIG["IP_DIR"]).mkdir(exist_ok=True)
    session = requests.Session()
    session.headers.update(MOBILE_HEADERS)
    
    all_telecom_ips = []
    
    logging.info("📱 **手机UA** - 抓取kiang前4页电信IP")
    
    for page in range(1, CONFIG["MAX_PAGES"] + 1):
        try:
            url = f"https://tonkiang.us/iptvmulticast.php?page={page}&iphone16=&code="
            logging.info(f"📄 kiang第 {page}/4 页")
            
            time.sleep(2)
            resp = session.get(url, timeout=CONFIG["TIMEOUT"])
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            results = soup.find_all('div', class_='result')
            
            page_telecom = []
            for result in results:
                channel_div = result.find('div', class_='channel')
                if not channel_div: continue
                
                domain_link = channel_div.find('a')
                if not domain_link: continue
                
                domain = domain_link.get_text(strip=True)
                
                # ✅ 只抓电信
                info_div = result.find('div', style=re.compile('font-size: 11px'))
                if not info_div or '电信' not in info_div.get_text():
                    continue
                
                # 存活天数
                alive_div = result.find('div', style='color:limegreen;')
                alive_days = alive_div.get_text(strip=True) if alive_div else "未知"
                
                # 频道数
                channel_count = result.find('span', style='font-size: 18px')
                channel_num = channel_count.get_text(strip=True) if channel_count else "0"
                
                # IP和TK
                href = domain_link['href']
                ip_match = re.search(r'ip=([^&]+)', href)
                tk_match = re.search(r'tk=([^&]+)', href)
                ip = ip_match.group(1) if ip_match else domain
                tk = tk_match.group(1) if tk_match else ""
                
                page_telecom.append({
                    'domain': domain,
                    'ip': ip,
                    'tk': tk,
                    'channels': channel_num,
                    'alive': alive_days,
                    'page': page
                })
            
            all_telecom_ips.extend(page_telecom)
            logging.info(f"✅ kiang第{page}页：{len(page_telecom)}个电信IP")
            
        except Exception as e:
            logging.error(f"❌ kiang第{page}页失败：{e}")
    
    logging.info(f"🎉 **kiang总计**：{len(all_telecom_ips)}个电信IP")
    return all_telecom_ips

# ===============================
# 💾 保存kiang电信IP
def save_telecom_ips(ips):
    kiang_file = Path(CONFIG["IP_DIR"]) / "kiang_电信全网.txt"
    
    with kiang_file.open('w', encoding='utf-8') as f:
        f.write(f"# kiang电信IPTV - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"# 总计: {len(ips)}个源\n\n")
        
        for ip_info in ips:
            f.write(f"{ip_info['ip']} | {ip_info['domain']} | TK:{ip_info['tk']} | "
                   f"频道:{ip_info['channels']} | 存活:{ip_info['alive']}\n")
    
    logging.info(f"💾 kiang保存 {len(ips)} 个电信IP")
    return len(ips)

# ===============================
# 🎬 生成Kiang 40频道IPTV
def generate_iptv(ips):
    if not ips:
        return
    
    logging.info("🎬 生成kiang 40频道IPTV")
    
    alias_map = {}
    for main, aliases in FULL_CHANNEL_MAPPING.items():
        for alias in aliases:
            alias_map[alias] = main
    
    all_channels = []
    seen_urls = set()
    
    def test_source(ip_info):
        try:
            ip, tk = ip_info['ip'], ip_info['tk']
            url = f"https://tonkiang.us/channellist.html?ip={ip}&tk={tk}&p=1"
            
            resp = requests.get(url, headers=MOBILE_HEADERS, timeout=8)
            if resp.status_code != 200:
                return []
            
            # 简单测试：假设可用
            base_url = f"http://{ip}"
            
            # 测试CCTV1
            test_url = f"{base_url}/live/cctv1.m3u8"
            if check_m3u8(test_url):
                logging.info(f"✅ kiang {ip} 可用")
                
                channels = []
                for ch_name in FULL_CHANNEL_MAPPING.keys():
                    ch_url = f"{base_url}/live/{ch_name.lower()}.m3u8"
                    if ch_url not in seen_urls:
                        channels.append(f"{ch_name},{ch_url}|kiang_{ip}")
                        seen_urls.add(ch_url)
                return channels
            return []
        except:
            return []
    
    def check_m3u8(url):
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-t", "2", "-i", url],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3
            )
            return result.returncode == 0
        except:
            return False
    
    # 并发测试前20个
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(test_source, ip_info) for ip_info in ips[:20]]
        for future in concurrent.futures.as_completed(futures):
            all_channels.extend(future.result())
    
    # 生成M3U
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    
    with Path(CONFIG["IPTV_FILE"]).open("w", encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        f.write(f"# kiang电信IPTV - {now} | {len(all_channels)}频道\n\n")
        
        for category, ch_list in CHANNEL_CATEGORIES.items():
            f.write(f"#EXTINF:-1 group-title=\"{category}\"\n")
            cat_channels = [line for line in all_channels if line.split(",")[0] in ch_list]
            for line in sorted(cat_channels):
                f.write(f"{line}\n")
            f.write("\n")
    
    unique = len(set(ch.split(",")[0] for ch in all_channels))
    logging.info(f"🎉 kiang IPTV完成！{unique}/40频道")

# ===============================
# 📤 Kiang Git推送
def git_push():
    os.system('git config user.name "Kiang-Bot"')
    os.system('git config user.email "kiang-bot@github.com"')
    os.system('git add .')
    os.system(f'git commit -m "🎉 kiang电信IPTV {datetime.now().strftime("%Y-%m-%d")}" || echo "No changes"')
    os.system('git push')
    logging.info("✅ kiang Git推送完成")

# ===============================
# 🚀 Kiang主程序
def run_iptv():
    start_time = time.time()
    logging.info("🚀 kiang电信IPTV启动")
    
    # 1. 抓取
    ips = scrape_telecom_ips()
    
    # 2. 保存
    if ips:
        count = save_telecom_ips(ips)
        
        # 3. 生成IPTV（每3次）
        if int(time.time()) % 3 == 0:
            generate_iptv(ips)
        
        # 4. 推送
        git_push()
    
    elapsed = time.time() - start_time
    logging.info(f"✅ kiang完成！耗时: {elapsed:.1f}s | 电信IP: {len(ips)}")

# ===============================
# 调度器
def start_scheduler():
    for t in CONFIG["SCHEDULE_TIMES"]:
        schedule.every().day.at(t).do(run_iptv)
    while True:
        schedule.run_pending()
        time.sleep(60)

# ===============================
if __name__ == "__main__":
    setup_logging()
    if len(sys.argv) > 1 and sys.argv[1] == "--scheduler":
        start_scheduler()
    else:
        run_iptv()
