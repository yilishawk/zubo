import os
import re
import requests
import time
import concurrent.futures
import subprocess
import random
import logging
from typing import Dict, List, Set, Tuple

# ===============================
# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('iptv_scanner.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===============================
# 安全配置
SAFE_CONFIG = {
    "max_workers": 8,
    "request_delay": 8,
    "timeout": 10,
    "max_retries": 2,
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
]

def get_safe_headers():
    """获取安全的请求头"""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

def safe_delay(min_delay: float = None, max_delay: float = None):
    """安全的延迟，避免请求过快"""
    if min_delay is None:
        min_delay = SAFE_CONFIG["request_delay"]
    if max_delay is None:
        max_delay = min_delay + 3
    
    delay = random.uniform(min_delay, max_delay)
    time.sleep(delay)

# ===============================
# 配置区
FOFA_URLS = {
    "https://fofa.info/result?qbase64=InVkcHh5IiAmJiBjb3VudHJ5PSJDTiI%3D": "ip.txt",
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
        "CCTV1", "CCTV2", "CCTV3", "CCTV4", "CCTV4欧洲", "CCTV4美洲", "CCTV5", "CCTV5+", "CCTV6", "CCTV7",
        "CCTV8", "CCTV9", "CCTV10", "CCTV11", "CCTV12", "CCTV13", "CCTV14", "CCTV15", "CCTV16", "CCTV17", "CCTV4K", "CCTV8K",
        "兵器科技", "风云音乐", "风云足球", "风云剧场", "怀旧剧场", "第一剧场", "女性时尚", "世界地理", "央视台球", "高尔夫网球",
        "央视文化精品", "卫生健康", "电视指南", "中学生", "发现之旅", "书法频道", "国学频道", "环球奇观"
    ],
    "卫视频道": [
        "湖南卫视", "浙江卫视", "江苏卫视", "东方卫视", "深圳卫视", "北京卫视", "广东卫视", "广西卫视", "东南卫视", "海南卫视",
        "河北卫视", "河南卫视", "湖北卫视", "江西卫视", "四川卫视", "重庆卫视", "贵州卫视", "云南卫视", "天津卫视", "安徽卫视",
        "山东卫视", "辽宁卫视", "黑龙江卫视", "吉林卫视", "内蒙古卫视", "宁夏卫视", "山西卫视", "陕西卫视", "甘肃卫视", "青海卫视",
        "新疆卫视", "西藏卫视", "三沙卫视", "兵团卫视", "延边卫视", "安多卫视", "康巴卫视", "农林卫视", "山东教育卫视",
        "中国教育1台", "中国教育2台", "中国教育3台", "中国教育4台", "早期教育"
    ],
    "数字频道": [
        "CHC动作电影", "CHC家庭影院", "CHC影迷电影", "淘电影", "淘精彩", "淘剧场", "淘4K", "淘娱乐", "淘BABY", "淘萌宠", "重温经典",
        "星空卫视", "CHANNEL[V]", "凤凰卫视中文台", "凤凰卫视资讯台", "凤凰卫视香港台", "凤凰卫视电影台", "求索纪录", "求索科学",
        "求索生活", "求索动物", "纪实人文", "金鹰纪实", "纪实科教", "睛彩青少", "睛彩竞技", "睛彩篮球", "睛彩广场舞", "魅力足球", "五星体育",
        "劲爆体育", "快乐垂钓", "茶频道", "先锋乒羽", "天元围棋", "汽摩", "梨园频道", "文物宝库", "武术世界", "哒啵赛事", "哒啵电竞", "黑莓电影", "黑莓动画", 
        "乐游", "生活时尚", "都市剧场", "欢笑剧场", "游戏风云", "金色学堂", "动漫秀场", "新动漫", "卡酷少儿", "金鹰卡通", "优漫卡通", "哈哈炫动", "嘉佳卡通", 
        "中国交通", "中国天气", "华数4K", "华数星影", "华数动作影院", "华数喜剧影院", "华数家庭影院", "华数经典电影", "华数热播剧场", "华数碟战剧场",
        "华数军旅剧场", "华数城市剧场", "华数武侠剧场", "华数古装剧场", "华数魅力时尚", "华数少儿动画", "华数动画"
    ],
    "湖北": [
        "湖北公共新闻", "湖北经视频道", "湖北综合频道", "湖北垄上频道", "湖北影视频道", "湖北生活频道", "湖北教育频道", "武汉新闻综合", "武汉电视剧", "武汉科技生活",
        "武汉文体频道", "武汉教育频道", "阳新综合", "房县综合", "蔡甸综合",
    ],
    "陕西电视": [
        "陕西卫视", "陕西新闻资讯", "陕西都市青春", "陕西银龄", "陕西秦腔", "陕西体育休闲", "陕西西部电影", "西安新闻综合", "西安电视台"
    ],
}

CHANNEL_MAPPING = {
    "CCTV1": ["CCTV-1", "CCTV-1 HD", "CCTV1 HD", "CCTV-1综合"],
    "CCTV2": ["CCTV-2", "CCTV-2 HD", "CCTV2 HD", "CCTV-2财经"],
    "CCTV3": ["CCTV-3", "CCTV-3 HD", "CCTV3 HD", "CCTV-3综艺"],
    "CCTV4": ["CCTV-4", "CCTV-4 HD", "CCTV4 HD", "CCTV-4中文国际"],
    "CCTV4欧洲": ["CCTV-4欧洲", "CCTV-4欧洲", "CCTV4欧洲 HD", "CCTV-4 欧洲", "CCTV-4中文国际欧洲", "CCTV4中文欧洲"],
    "CCTV4美洲": ["CCTV-4美洲", "CCTV-4北美", "CCTV4美洲 HD", "CCTV-4 美洲", "CCTV-4中文国际美洲", "CCTV4中文美洲"],
    "CCTV5": ["CCTV-5", "CCTV-5 HD", "CCTV5 HD", "CCTV-5体育"],
    "CCTV5+": ["CCTV-5+", "CCTV-5+ HD", "CCTV5+ HD", "CCTV-5+体育赛事"],
    "CCTV6": ["CCTV-6", "CCTV-6 HD", "CCTV6 HD", "CCTV-6电影"],
    "CCTV7": ["CCTV-7", "CCTV-7 HD", "CCTV7 HD", "CCTV-7国防军事"],
    "CCTV8": ["CCTV-8", "CCTV-8 HD", "CCTV8 HD", "CCTV-8电视剧"],
    "CCTV9": ["CCTV-9", "CCTV-9 HD", "CCTV9 HD", "CCTV-9纪录"],
    "CCTV10": ["CCTV-10", "CCTV-10 HD", "CCTV10 HD", "CCTV-10科教"],
    "CCTV11": ["CCTV-11", "CCTV-11 HD", "CCTV11 HD", "CCTV-11戏曲"],
    "CCTV12": ["CCTV-12", "CCTV-12 HD", "CCTV12 HD", "CCTV-12社会与法"],
    "CCTV13": ["CCTV-13", "CCTV-13 HD", "CCTV13 HD", "CCTV-13新闻"],
    "CCTV14": ["CCTV-14", "CCTV-14 HD", "CCTV14 HD", "CCTV-14少儿"],
    "CCTV15": ["CCTV-15", "CCTV-15 HD", "CCTV15 HD", "CCTV-15音乐"],
    "CCTV16": ["CCTV-16", "CCTV-16 HD", "CCTV-16 4K", "CCTV-16奥林匹克", "CCTV16 4K", "CCTV-16奥林匹克4K"],
    "CCTV17": ["CCTV-17", "CCTV-17 HD", "CCTV17 HD", "CCTV-17农业农村"],
    "CCTV4K": ["CCTV4K超高清", "CCTV-4K超高清", "CCTV-4K 超高清", "CCTV 4K"],
    "CCTV8K": ["CCTV8K超高清", "CCTV-8K超高清", "CCTV-8K 超高清", "CCTV 8K"],
    "兵器科技": ["CCTV-兵器科技", "CCTV兵器科技"],
    "风云音乐": ["CCTV-风云音乐", "CCTV风云音乐"],
    "第一剧场": ["CCTV-第一剧场", "CCTV第一剧场"],
    "风云足球": ["CCTV-风云足球", "CCTV风云足球"],
    "风云剧场": ["CCTV-风云剧场", "CCTV风云剧场"],
    "怀旧剧场": ["CCTV-怀旧剧场", "CCTV怀旧剧场"],
    "女性时尚": ["CCTV-女性时尚", "CCTV女性时尚"],
    "世界地理": ["CCTV-世界地理", "CCTV世界地理"],
    "央视台球": ["CCTV-央视台球", "CCTV央视台球"],
    "高尔夫网球": ["CCTV-高尔夫网球", "CCTV高尔夫网球", "CCTV央视高网", "CCTV-高尔夫·网球", "央视高网"],
    "央视文化精品": ["CCTV-央视文化精品", "CCTV央视文化精品", "CCTV文化精品", "CCTV-文化精品", "文化精品"],
    "卫生健康": ["CCTV-卫生健康", "CCTV卫生健康"],
    "电视指南": ["CCTV-电视指南", "CCTV电视指南"],
    "农林卫视": ["陕西农林卫视"],
    "三沙卫视": ["海南三沙卫视"],
    "兵团卫视": ["新疆兵团卫视"],
    "延边卫视": ["吉林延边卫视"],
    "安多卫视": ["青海安多卫视"],
    "康巴卫视": ["四川康巴卫视"],
    "山东教育卫视": ["山东教育"],
    "中国教育1台": ["CETV1", "中国教育一台", "中国教育1", "CETV-1 综合教育", "CETV-1"],
    "中国教育2台": ["CETV2", "中国教育二台", "中国教育2", "CETV-2 空中课堂", "CETV-2"],
    "中国教育3台": ["CETV3", "中国教育三台", "中国教育3", "CETV-3 教育服务", "CETV-3"],
    "中国教育4台": ["CETV4", "中国教育四台", "中国教育4", "CETV-4 职业教育", "CETV-4"],
    "早期教育": ["中国教育5台", "中国教育五台", "CETV早期教育", "华电早期教育", "CETV 早期教育"],
    "湖南卫视": ["湖南卫视4K"],
    "北京卫视": ["北京卫视4K"],
    "东方卫视": ["东方卫视4K"],
    "广东卫视": ["广东卫视4K"],
    "深圳卫视": ["深圳卫视4K"],
    "山东卫视": ["山东卫视4K"],
    "四川卫视": ["四川卫视4K"],
    "浙江卫视": ["浙江卫视4K"],
    "CHC影迷电影": ["CHC高清电影", "CHC-影迷电影", "影迷电影", "chc高清电影"],
    "淘电影": ["IPTV淘电影", "北京IPTV淘电影", "北京淘电影"],
    "淘精彩": ["IPTV淘精彩", "北京IPTV淘精彩", "北京淘精彩"],
    "淘剧场": ["IPTV淘剧场", "北京IPTV淘剧场", "北京淘剧场"],
    "淘4K": ["IPTV淘4K", "北京IPTV4K超清", "北京淘4K", "淘4K", "淘 4K"],
    "淘娱乐": ["IPTV淘娱乐", "北京IPTV淘娱乐", "北京淘娱乐"],
    "淘BABY": ["IPTV淘BABY", "北京IPTV淘BABY", "北京淘BABY", "IPTV淘baby", "北京IPTV淘baby", "北京淘baby"],
    "淘萌宠": ["IPTV淘萌宠", "北京IPTV萌宠TV", "北京淘萌宠"],
    "魅力足球": ["上海魅力足球"],
    "睛彩青少": ["睛彩羽毛球"],
    "求索纪录": ["求索记录", "求索纪录4K", "求索记录4K", "求索纪录 4K", "求索记录 4K"],
    "金鹰纪实": ["湖南金鹰纪实", "金鹰记实"],
    "纪实科教": ["北京纪实科教", "BRTV纪实科教", "纪实科教8K"],
    "星空卫视": ["星空衛視", "星空衛视", "星空卫視"],
    "CHANNEL[V]": ["CHANNEL-V", "Channel[V]"],
    "凤凰卫视中文台": ["凤凰中文", "凤凰中文台", "凤凰卫视中文", "凤凰卫视"],
    "凤凰卫视香港台": ["凤凰香港台", "凤凰卫视香港", "凤凰香港"],
    "凤凰卫视资讯台": ["凤凰资讯", "凤凰资讯台", "凤凰咨询", "凤凰咨询台", "凤凰卫视咨询台", "凤凰卫视资讯", "凤凰卫视咨询"],
    "凤凰卫视电影台": ["凤凰电影", "凤凰电影台", "凤凰卫视电影", "鳳凰衛視電影台", " 凤凰电影"],
    "茶频道": ["湖南茶频道"],
    "快乐垂钓": ["湖南快乐垂钓"],
    "先锋乒羽": ["湖南先锋乒羽"],
    "天元围棋": ["天元围棋频道"],
    "汽摩": ["重庆汽摩", "汽摩频道", "重庆汽摩频道"],
    "梨园频道": ["河南梨园频道", "梨园", "河南梨园"],
    "文物宝库": ["河南文物宝库"],
    "武术世界": ["河南武术世界"],
    "乐游": ["乐游频道", "上海乐游频道", "乐游纪实", "SiTV乐游频道", "SiTV 乐游频道"],
    "欢笑剧场": ["上海欢笑剧场4K", "欢笑剧场 4K", "欢笑剧场4K", "上海欢笑剧场"],
    "生活时尚": ["生活时尚4K", "SiTV生活时尚", "上海生活时尚"],
    "都市剧场": ["都市剧场4K", "SiTV都市剧场", "上海都市剧场"],
    "游戏风云": ["游戏风云4K", "SiTV游戏风云", "上海游戏风云"],
    "金色学堂": ["金色学堂4K", "SiTV金色学堂", "上海金色学堂"],
    "动漫秀场": ["动漫秀场4K", "SiTV动漫秀场", "上海动漫秀场"],
    "卡酷少儿": ["北京KAKU少儿", "BRTV卡酷少儿", "北京卡酷少儿", "卡酷动画"],
    "哈哈炫动": ["炫动卡通", "上海哈哈炫动"],
    "优漫卡通": ["江苏优漫卡通", "优漫漫画"],
    "金鹰卡通": ["湖南金鹰卡通"],
    "中国交通": ["中国交通频道"],
    "中国天气": ["中国天气频道"],
    "华数4K": ["华数低于4K", "华数4K电影", "华数爱上4K"],
    "陕西卫视": ["陕西卫视HD", "陕西卫视4K", "陕西卫视 高清"],
    "陕西新闻资讯": ["陕西新闻", "陕西新闻资讯HD", "陕西资讯"],
    "陕西都市青春": ["陕西都市", "陕西青春", "陕西都市青春HD"],
    "陕西银龄": ["陕西银龄频道", "陕西银龄HD"],
    "陕西秦腔": ["陕西秦腔戏曲", "秦腔频道", "陕西秦腔HD"],
    "陕西体育休闲": ["陕西体育", "陕西休闲", "陕西体育休闲HD"],
    "陕西西部电影": ["陕西西部", "陕西电影", "陕西西部电影HD"],
    "西安新闻综合": ["西安新闻", "西安综合", "西安新闻综合HD"],
    "西安电视台": ["西安TV", "西安电视台HD", "西安综合电视台"],
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
    # 修改：由于每天只运行2次，调整为7天清理一次（14次运行）
    if count >= 14:
        logger.info(f"🧹 第 {count} 次运行，清空 {IP_DIR} 下所有 .txt 文件")
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
    all_ips = set()
    for url, filename in FOFA_URLS.items():
        logger.info(f"📡 正在爬取 {filename} ...")
        
        try:
            headers = get_safe_headers()
            r = requests.get(url, headers=headers, timeout=SAFE_CONFIG["timeout"])
            logger.info(f"📄 响应状态码: {r.status_code}")
            
            # 多种方式提取IP
            urls_all = re.findall(r'<a href="http://(.*?)"', r.text)
            logger.info(f"🎯 正则提取到 {len(urls_all)} 个IP")
            
            # 备用提取方法
            ip_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+\b'
            alt_matches = re.findall(ip_pattern, r.text)
            if alt_matches:
                logger.info(f"🎯 备用方法找到 {len(alt_matches)} 个IP")
                all_ips.update(alt_matches)
            
            all_ips.update(u.strip() for u in urls_all)
            logger.info(f"✅ 从 {filename} 总共获取到 {len(all_ips)} 个IP")
            
        except Exception as e:
            logger.error(f"❌ 爬取失败：{e}")
        
        safe_delay()
    
    if not all_ips:
        logger.warning("⚠️ 没有获取到任何IP地址")
        count = get_run_count() + 1
        save_run_count(count)
        return count

    # IP地理位置查询
    province_isp_dict = {}
    total_ips = len(all_ips)
    processed = 0
    
    for ip_port in all_ips:
        try:
            ip = ip_port.split(":")[0]
            headers = get_safe_headers()
            res = requests.get(f"http://ip-api.com/json/{ip}?lang=zh-CN", headers=headers, timeout=SAFE_CONFIG["timeout"])
            
            if res.status_code == 200:
                data = res.json()
                province = data.get("regionName", "未知")
                isp = get_isp(ip)
                
                if isp != "未知":
                    fname = f"{province}{isp}.txt"
                    province_isp_dict.setdefault(fname, set()).add(ip_port)
            
            processed += 1
            if processed % 10 == 0:
                logger.info(f"🌍 IP地理位置查询进度: {processed}/{total_ips}")
                safe_delay(3, 5)
                
        except Exception as e:
            logger.warning(f"⚠️ IP地理位置查询异常: {ip_port}, 错误: {e}")
            continue

    mode, run_count = check_and_clear_files_by_run_count()
    
    if not province_isp_dict:
        logger.warning("⚠️ 没有成功分类的IP地址")
        return run_count
        
    for filename, ip_set in province_isp_dict.items():
        path = os.path.join(IP_DIR, filename)
        with open(path, mode, encoding="utf-8") as f:
            for ip_port in sorted(ip_set):
                f.write(ip_port + "\n")
        logger.info(f"📝 {path} 已{'覆盖' if mode=='w' else '追加'}写入 {len(ip_set)} 个 IP")
    
    logger.info(f"✅ 第一阶段完成，当前轮次：{run_count}")
    return run_count

# ===============================
# 第二阶段
def second_stage():
    logger.info("🔔 第二阶段：生成 zubo.txt")
    combined_lines = []
    
    if not os.path.exists(IP_DIR):
        logger.error("❌ IP目录不存在")
        return
        
    if not os.path.exists(RTP_DIR):
        logger.error("❌ RTP目录不存在")
        return
    
    ip_files = [f for f in os.listdir(IP_DIR) if f.endswith(".txt")]
    rtp_files = [f for f in os.listdir(RTP_DIR) if f.endswith(".txt")]
    
    logger.info(f"📁 发现 {len(ip_files)} 个IP文件和 {len(rtp_files)} 个RTP文件")
    
    for ip_file in ip_files:
        if ip_file not in rtp_files:
            logger.warning(f"⚠️ 没有对应的RTP文件: {ip_file}")
            continue
            
        ip_path = os.path.join(IP_DIR, ip_file)
        rtp_path = os.path.join(RTP_DIR, ip_file)

        try:
            with open(ip_path, encoding="utf-8") as f1, open(rtp_path, encoding="utf-8") as f2:
                ip_lines = [x.strip() for x in f1 if x.strip()]
                rtp_lines = [x.strip() for x in f2 if x.strip()]

            logger.info(f"🔗 处理 {ip_file}: {len(ip_lines)}个IP × {len(rtp_lines)}个频道")
            
            if not ip_lines or not rtp_lines:
                continue

            for ip_port in ip_lines:
                for rtp_line in rtp_lines:
                    if "," not in rtp_line:
                        continue
                    ch_name, rtp_url = rtp_line.split(",", 1)
                    if "rtp://" in rtp_url:
                        combined_url = f"http://{ip_port}/rtp/{rtp_url.split('rtp://')[1]}"
                        combined_lines.append(f"{ch_name},{combined_url}")

        except Exception as e:
            logger.error(f"❌ 处理文件 {ip_file} 时出错: {e}")
            continue

    logger.info(f"📊 组合完成，共 {len(combined_lines)} 行")
    
    # 去重
    unique = {}
    for line in combined_lines:
        url_part = line.split(",", 1)[1]
        if url_part not in unique:
            unique[url_part] = line

    logger.info(f"🎯 去重后: {len(unique)} 条唯一URL")

    with open(ZUBO_FILE, "w", encoding="utf-8") as f:
        for line in unique.values():
            f.write(line + "\n")
    logger.info(f"✅ zubo.txt 生成完成")

# ===============================
# 第三阶段 - 超快速IP测速方案
def fast_ip_test(ip_port: str) -> Tuple[bool, float, float]:
    """
    对每个IP只测试一个代表频道（默认CCTV1）
    返回: (是否成功, 连接延迟, 速度评分)
    """
    # 构造测试URL - 这里需要根据实际情况调整
    test_url = f"http://{ip_port}/rtp/239.76.245.115:1234"  # 示例CCTV1地址
    
    try:
        start_time = time.time()
        
        # 使用ffprobe快速检测
        result = subprocess.run([
            "ffprobe", "-v", "quiet",
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_name",
            "-of", "csv=p=0",
            "-timeout", "3000000",  # 3秒超时(微秒)
            test_url
        ], capture_output=True, timeout=3, text=True)
        
        probe_time = time.time() - start_time
        
        if result.returncode == 0 and result.stdout.strip():
            # 成功获取流信息
            response_score = max(0, 10 - probe_time * 2)
            return True, probe_time, response_score
        else:
            return False, probe_time, 0
            
    except subprocess.TimeoutExpired:
        return False, 3, 0
    except Exception as e:
        return False, 10, 0

def ip_speed_test_worker(ip_data: Tuple[str, str]) -> Tuple[str, str, bool, float, float]:
    """IP测速工作线程"""
    ip_port, provider = ip_data
    success, latency, score = fast_ip_test(ip_port)
    return ip_port, provider, success, latency, score

def fast_ip_based_sorting() -> Dict[str, List[Tuple]]:
    """
    基于IP测速的快速排序方案
    每个IP只测试一个代表频道，然后为每个频道选择最快的前2个IP
    """
    logger.info("🚀 开始基于IP的快速测速排序...")
    
    # 收集所有IP
    all_ips = []
    ip_to_provider = {}
    
    for fname in os.listdir(IP_DIR):
        if not fname.endswith(".txt"):
            continue
        province_operator = fname.replace(".txt", "")
        path = os.path.join(IP_DIR, fname)
        
        with open(path, encoding="utf-8") as f:
            for line in f:
                ip_port = line.strip()
                if ip_port and ":" in ip_port:
                    all_ips.append((ip_port, province_operator))
                    ip_to_provider[ip_port] = province_operator
    
    logger.info(f"📡 发现 {len(all_ips)} 个IP需要测速")
    
    if not all_ips:
        logger.warning("⚠️ 没有找到可用的IP文件")
        return {}
    
    # 对IP进行测速
    ip_speed_results = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=SAFE_CONFIG["max_workers"]) as executor:
        future_to_ip = {executor.submit(ip_speed_test_worker, ip_data): ip_data for ip_data in all_ips}
        
        completed = 0
        for future in concurrent.futures.as_completed(future_to_ip):
            ip_data = future_to_ip[future]
            try:
                ip_port, provider, success, latency, score = future.result(timeout=10)
                completed += 1
                
                if success:
                    ip_speed_results[ip_port] = (provider, score, latency)
                    status = "✅"
                else:
                    status = "❌"
                
                if completed % 10 == 0:
                    logger.info(f"  [{completed}/{len(all_ips)}] {status} {ip_port} | 延迟: {latency:.2f}s | 评分: {score:.1f}")
                
            except Exception as e:
                completed += 1
                logger.warning(f"  ⚠️ IP测速失败: {ip_data[0]}, 错误: {e}")
    
    # 获取可用的快速IP列表（按评分排序）
    available_ips = [(ip, provider, score) for ip, (provider, score, latency) in ip_speed_results.items()]
    available_ips.sort(key=lambda x: x[2], reverse=True)  # 按评分降序
    
    logger.info(f"📊 IP测速完成: {len(available_ips)}/{len(all_ips)} 个IP可用")
    
    # 构建频道到IP的映射
    channel_to_ips = {}
    
    if not os.path.exists(ZUBO_FILE):
        logger.error("❌ zubo.txt 文件不存在")
        return {}
        
    with open(ZUBO_FILE, encoding="utf-8") as f:
        for line in f:
            if "," not in line:
                continue
            ch_name, url = line.strip().split(",", 1)
            
            # 提取IP
            m = re.match(r"http://(\d+\.\d+\.\d+\.\d+:\d+)/", url)
            if m:
                ip_port = m.group(1)
                
                # 如果这个IP是可用的，添加到频道映射
                if ip_port in ip_speed_results:
                    provider, score, latency = ip_speed_results[ip_port]
                    
                    # 标准化频道名称
                    main_channel = ch_name
                    for main_ch, aliases in CHANNEL_MAPPING.items():
                        if ch_name in aliases or ch_name == main_ch:
                            main_channel = main_ch
                            break
                    
                    channel_to_ips.setdefault(main_channel, []).append((ch_name, url, provider, score))
    
    # 为每个频道选择最快的前2个源
    final_channels = {}
    for channel, sources in channel_to_ips.items():
        # 按评分排序并取前2个
        sources.sort(key=lambda x: x[3], reverse=True)
        final_channels[channel] = sources[:2]  # 只保留前2个最快的
    
    logger.info(f"🎯 频道处理完成: {len(final_channels)} 个频道，每个频道保留2个最快源")
    
    return final_channels

def priority_based_selection(sorted_channels: Dict, priority_channels: List[str] = None) -> Dict:
    """
    基于频道优先级的源选择策略
    重要频道保留2个源，次要频道保留1个源
    """
    if priority_channels is None:
        # 默认重要频道列表
        priority_channels = [
            "CCTV1", "CCTV2", "CCTV3", "CCTV4", "CCTV5", "CCTV5+", "CCTV6", "CCTV7", "CCTV8",
            "CCTV9", "CCTV10", "CCTV11", "CCTV12", "CCTV13", "CCTV14", "CCTV15", "CCTV16", "CCTV17",
            "湖南卫视", "浙江卫视", "江苏卫视", "北京卫视", "东方卫视", "广东卫视", "深圳卫视"
        ]
    
    optimized_channels = {}
    
    for channel, sources in sorted_channels.items():
        if channel in priority_channels:
            # 重要频道：保留2个最快源
            optimized_channels[channel] = sources[:2]
        else:
            # 次要频道：只保留1个最快源
            optimized_channels[channel] = sources[:1] if sources else []
    
    # 统计
    priority_count = sum(1 for ch in optimized_channels if ch in priority_channels)
    normal_count = len(optimized_channels) - priority_count
    total_sources = sum(len(sources) for sources in optimized_channels.values())
    
    logger.info(f"🎯 优先级优化: {priority_count}个重要频道(2源), {normal_count}个普通频道(1源), 共{total_sources}个源")
    
    return optimized_channels

def generate_optimized_iptv(sorted_channels: Dict):
    """生成优化的IPTV文件，每个频道只保留1-2个最快源"""
    
    with open(IPTV_FILE, "w", encoding="utf-8") as f:
        for category, channel_list in CHANNEL_CATEGORIES.items():
            f.write(f"{category},#genre#\n")
            
            channel_count = 0
            for channel in channel_list:
                if channel in sorted_channels:
                    sources = sorted_channels[channel]
                    channel_count += 1
                    
                    # 写入源
                    for ch_name, url, provider, score in sources:
                        f.write(f"{ch_name},{url}${provider}\n")
            
            f.write("\n")
            logger.info(f"  📁 {category}: {channel_count} 个频道")
    
    # 统计信息
    total_channels = len(sorted_channels)
    total_sources = sum(len(sources) for sources in sorted_channels.values())
    
    logger.info(f"🎯 优化版 IPTV.txt 生成完成！")
    logger.info(f"📊 统计: {total_channels} 个频道, {total_sources} 个源")
    logger.info(f"🚀 重要频道保留2个最快源，普通频道保留1个最快源")

def ultra_fast_third_stage():
    """超快速的第三阶段：基于IP测速，每个频道只保留1-2个最快源"""
    logger.info("🧩 第三阶段：超快速IP测速排序生成优化版 IPTV.txt")
    
    if not os.path.exists(ZUBO_FILE):
        logger.warning("⚠️ zubo.txt 不存在，跳过")
        return
    
    start_time = time.time()
    
    # 使用基于IP的快速测速
    sorted_channels = fast_ip_based_sorting()
    
    if not sorted_channels:
        logger.error("❌ 没有可用的频道数据，跳过IPTV文件生成")
        return
    
    # 应用优先级策略
    priority_channels = [
        "CCTV1", "CCTV2", "CCTV3", "CCTV4", "CCTV5", "CCTV5+", "CCTV6", "CCTV7", "CCTV8",
        "CCTV9", "CCTV10", "CCTV11", "CCTV12", "CCTV13", "CCTV14", "CCTV15", "CCTV16", "CCTV17",
        "湖南卫视", "浙江卫视", "江苏卫视", "北京卫视", "东方卫视", "广东卫视", "深圳卫视",
        "CCTV4K", "CCTV8K", "CCTV4欧洲", "CCTV4美洲"
    ]
    optimized_channels = priority_based_selection(sorted_channels, priority_channels)
    
    # 生成优化版IPTV文件
    generate_optimized_iptv(optimized_channels)
    
    elapsed_time = time.time() - start_time
    logger.info(f"⏱️ 第三阶段耗时: {elapsed_time:.1f} 秒")

# ===============================
# 文件推送  
def push_all_files():
    logger.info("🚀 推送所有更新文件到 GitHub...")
    os.system('git config --global user.name "github-actions"')
    os.system('git config --global user.email "github-actions@users.noreply.github.com"')
    os.system("git add 计数.txt")
    os.system("git add ip/*.txt || true")
    os.system("git add IPTV.txt || true")
    os.system('git commit -m "自动更新：计数、IP文件、IPTV.txt" || echo "⚠️ 无需提交"')
    os.system("git push origin main || echo '⚠️ 推送失败'")

# ===============================
# 主执行逻辑
if __name__ == "__main__":
    try:
        logger.info("🎬 开始执行 FOFA IPTV 扫描脚本")
        start_time = time.time()
        
        run_count = first_stage()
        
        # 修改：每次运行都执行第二、三阶段
        logger.info("🚀 开始执行第二阶段...")
        second_stage()
        
        logger.info("🚀 开始执行第三阶段...")
        ultra_fast_third_stage()
        
        push_all_files()
        
        total_time = time.time() - start_time
        logger.info(f"🎉 脚本执行完成！总耗时: {total_time:.2f} 秒")
        
    except Exception as e:
        logger.error(f"💥 脚本执行异常: {e}")
        # 不推送任何内容，确保安全
