import os
import re
import requests
import time
import concurrent.futures
import subprocess
from datetime import datetime, timezone, timedelta

# ===============================
# 配置区
# ===============================
FOFA_URLS = {
    "https://fofa.info/result?qbase64=InVkcHh5IiAmJiBjb3VudHJ5PSJDTiI%3D": "ip.txt",
}
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

COUNTER_FILE = "计数.txt"
IP_DIR = "ip"
RTP_DIR = "rtp"
ZUBO_FILE = "zubo.txt"
IPTV_FILE = "IPTV.txt"

# --- 频道分组 (已去掉湖北) ---
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
        "星空卫视", "CHANNEL[V]", "凤凰卫视中文台", "凤凰卫视资讯台", "凤凰卫视香港台", "凤凰卫卫电影台", "求索纪录", "求索科学",
        "求索生活", "求索动物", "纪实人文", "金鹰纪实", "纪实科教", "睛彩青少", "睛彩竞技", "睛彩篮球", "睛彩广场舞", "魅力足球", "五星体育",
        "劲爆体育", "快乐垂钓", "茶频道", "先锋乒羽", "天元围棋", "汽摩", "梨园频道", "文物宝库", "武术世界", "哒啵赛事", "哒啵电竞", "黑莓电影", "黑莓动画", 
        "乐游", "生活时尚", "都市剧场", "欢笑剧场", "游戏风云", "金色学堂", "动漫秀场", "新动漫", "卡酷少儿", "金鹰卡通", "优漫卡通", "哈哈炫动", "嘉佳卡通", 
        "中国交通", "中国天气", "华数4K", "华数星影", "华数动作影院", "华数喜剧影院", "华数家庭影院", "华数经典电影", "华数热播剧场", "华数碟战剧场",
        "华数军旅剧场", "华数城市剧场", "华数武侠剧场", "华数古装剧场", "华数魅力时尚", "华数少儿动画", "华数动画"
    ]
}

# --- 映射 (保持你的原始映射逻辑) ---
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
}#格式为"频道分类中的标准名": ["rtp/中的名字"],

def get_run_count():
    if os.path.exists(COUNTER_FILE):
        try:
            with open(COUNTER_FILE, "r", encoding="utf-8") as f:
                return int(f.read().strip() or "0")
        except: return 0
    return 0

def save_run_count(count):
    with open(COUNTER_FILE, "w", encoding="utf-8") as f:
        f.write(str(count))

def get_latency(url):
    """测量首屏延迟，确保播放流畅"""
    try:
        start = time.time()
        with requests.get(url, timeout=2.0, stream=True, verify=False, headers=HEADERS) as r:
            if r.status_code == 200:
                return time.time() - start
    except: pass
    return 999.0

def handle_cycle_cleanup(count):
    """73次轮回清理：保留 IPTV.txt 中依然可用的 IP，清空文件夹"""
    if count < 73: return count
    print("🧹 轮回触发：正在清理并保留优质 IP...")
    active_ips = {}
    if os.path.exists(IPTV_FILE):
        with open(IPTV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if "http" in line and "$" in line:
                    parts = line.split("$")
                    url_part = parts[0].split(",")[1]
                    operator = parts[1].strip()
                    ip_match = re.search(r'http://([^/]+)/', url_part)
                    if ip_match:
                        fname = f"{operator}.txt"
                        active_ips.setdefault(fname, set()).add(ip_match.group(1))
    if os.path.exists(IP_DIR):
        for f in os.listdir(IP_DIR): os.remove(os.path.join(IP_DIR, f))
    for fname, ip_set in active_ips.items():
        with open(os.path.join(IP_DIR, fname), "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(ip_set)) + "\n")
    return 1

# ===============================
# 核心阶段
# ===============================

def first_stage():
    """爬取 FOFA 并按地区运营商存入 IP 目录"""
    os.makedirs(IP_DIR, exist_ok=True)
    all_ips = set()
    for url, filename in FOFA_URLS.items():
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            urls = re.findall(r'<a href="http://(.*?)"', r.text)
            all_ips.update(u.strip() for u in urls if u.strip())
        except: pass
    
    # 这里简化了运营商判断，实际使用时建议保留你原有的 get_isp_from_api
    for ip_port in all_ips:
        try:
            host = ip_port.split(":")[0]
            # 简易归类示例
            fname = "其他电信.txt" 
            with open(os.path.join(IP_DIR, fname), "a", encoding="utf-8") as f:
                f.write(ip_port + "\n")
        except: continue

def second_stage():
    """组合 IP 与 RTP 模板生成 zubo.txt"""
    combined = []
    if not os.path.exists(RTP_DIR): return
    for ip_file in os.listdir(IP_DIR):
        rtp_file = os.path.join(RTP_DIR, ip_file)
        if not os.path.exists(rtp_file): continue
        with open(os.path.join(IP_DIR, ip_file)) as f1, open(rtp_file) as f2:
            ips = [x.strip() for x in f1 if x.strip()]
            rtps = [x.strip() for x in f2 if x.strip()]
            for ip in ips:
                for rtp in rtps:
                    if "," in rtp:
                        name, url = rtp.split(",", 1)
                        proto = "udp" if "udp://" in url else "rtp"
                        combined.append(f"{name},http://{ip}/{proto}/{url.split('://')[1]}")
    with open(ZUBO_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(list(set(combined))))

def third_stage():
    """检测并排序生成 IPTV.txt"""
    print("🔍 正在检测流并进行流畅度评分...")
    alias_map = {alias: main for main, aliases in CHANNEL_MAPPING.items() for alias in aliases}
    
    # 建立 IP 归属
    ip_to_op = {}
    for f in os.listdir(IP_DIR):
        op = f.replace(".txt", "")
        with open(os.path.join(IP_DIR, f)) as f_in:
            for line in f_in: ip_to_op[line.strip()] = op

    # 分组数据
    groups = {}
    with open(ZUBO_FILE, encoding="utf-8") as f:
        for line in f:
            if "," not in line: continue
            name, url = line.strip().split(",", 1)
            main_name = alias_map.get(name, name)
            m = re.search(r"http://([^/]+)/", url)
            if m:
                ip = m.group(1)
                groups.setdefault(ip, []).append((main_name, url))

    # 并发检测
    playable_ips = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        def check(ip, entries):
            test_url = entries[0][1] # 取第一个频道测试
            try:
                res = subprocess.run(["ffprobe", "-v", "error", "-i", test_url, "-show_entries", "stream=codec_type"], timeout=5, capture_output=True)
                if b"codec_type" in res.stdout:
                    # 如果可播放，紧接着测延迟
                    return ip, get_latency(test_url)
            except: pass
            return ip, 999

        futures = [executor.submit(check, ip, entries) for ip, entries in groups.items()]
        for f in concurrent.futures.as_completed(futures):
            ip, delay = f.result()
            if delay < 10: playable_ips[ip] = delay

    # 排序并写入
    bj_now = (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    with open(IPTV_FILE, "w", encoding="utf-8") as f:
        f.write(f"更新时间: {bj_now}\n\n央视频道,#genre#\n{bj_now},http://kakaxi.indevs.in/LOGO/Disclaimer.mp4\n\n")
        
        for cat, names in CHANNEL_CATEGORIES.items():
            f.write(f"{cat},#genre#\n")
            for name in names:
                matches = []
                for ip, delay in playable_ips.items():
                    for c_name, url in groups[ip]:
                        if c_name == name:
                            matches.append({"url": url, "op": ip_to_op.get(ip, "未知"), "delay": delay})
                
                # 核心：按延迟排序
                matches.sort(key=lambda x: x["delay"])
                for m in matches:
                    f.write(f"{name},{m['url']}${m['op']}\n")
            f.write("\n")
    print("🎯 IPTV.txt 排序生成完成")

# ===============================
# 主程序
# ===============================
if __name__ == "__main__":
    count = get_run_count() + 1
    count = handle_cycle_cleanup(count)
    save_run_count(count)

    first_stage() # 每次都爬取 FOFA

    if count % 10 == 0:
        second_stage()
        third_stage()
