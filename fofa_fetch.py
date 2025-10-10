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
# 第二阶段：生成 zubo.txt
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

        province_operator = ip_file.replace(".txt", "")
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

    # 去重
    unique_lines = {}
    for line in combined_lines:
        parts = line.split(",", 1)
        if len(parts) == 2:
            url_part = parts[1].split("$")[0]
            if url_part not in unique_lines:
                unique_lines[url_part] = line
    combined_lines = list(unique_lines.values())

    # 写入 zubo.txt
    with open(ZUBO_FILE, "w", encoding="utf-8") as f:
        for line in combined_lines:
            f.write(line + "\n")

    print(f"🎯 第二阶段完成，已生成 {ZUBO_FILE}，共 {len(combined_lines)} 条有效 URL")

    # ===============================
    # 第三阶段：播放性检测 + CCTV1判断 + 分类映射
    print("🚀 第三阶段：播放性检测 + 分类映射")
    final_lines = []

    # 准备频道分类和映射
    CHANNEL_CATEGORIES = {
    "央视频道": ["CCTV1", "CCTV2", "CCTV3", "CCTV4", "CCTV4欧洲", "CCTV4美洲", "CCTV5", "CCTV5+", "CCTV6", "CCTV7",
        "CCTV8", "CCTV9", "CCTV10", "CCTV11", "CCTV12", "CCTV13", "CCTV14", "CCTV15", "CCTV16", "CCTV17", "CCTV4K", "CCTV8K",
        "兵器科技", "风云音乐", "风云足球", "风云剧场", "怀旧剧场", "第一剧场", "女性时尚", "世界地理", "央视台球", "高尔夫网球",
        "央视文化精品", "卫生健康", "电视指南"],
    "卫视频道": ["湖南卫视", "浙江卫视", "江苏卫视", "东方卫视", "深圳卫视", "北京卫视", "广东卫视", "广西卫视", "东南卫视", "海南卫视",
        "河北卫视", "河南卫视", "湖北卫视", "江西卫视", "四川卫视", "重庆卫视", "贵州卫视", "云南卫视", "天津卫视", "安徽卫视",
        "山东卫视", "辽宁卫视", "黑龙江卫视", "吉林卫视", "内蒙古卫视", "宁夏卫视", "山西卫视", "陕西卫视", "甘肃卫视", "青海卫视",
        "新疆卫视", "西藏卫视", "三沙卫视", "兵团卫视", "延边卫视", "安多卫视", "康巴卫视", "农林卫视", "山东教育卫视",
        "中国教育1台", "中国教育2台", "中国教育3台", "中国教育4台", "早期教育"],
    "数字频道": ["CHC动作电影", "CHC家庭影院", "CHC影迷电影", "淘电影", "淘精彩", "淘剧场", "淘4K", "淘娱乐", "淘BABY", "淘萌宠", "重温经典",
        "星空卫视", "CHANNEL[V]", "凤凰卫视中文台", "凤凰卫视资讯台", "凤凰卫视香港台", "凤凰卫视电影台", "求索纪录", "求索科学",
        "求索生活", "求索动物", "纪实人文", "金鹰纪实", "纪实科教", "睛彩青少", "睛彩竞技", "睛彩篮球", "睛彩广场舞", "魅力足球", "五星体育",
        "劲爆体育", "快乐垂钓", "茶频道", "先锋乒羽", "天元围棋", "汽摩", "梨园频道", "文物宝库", "武术世界", "哒啵赛事", "哒啵电竞", "黑莓电影", "黑莓动画", 
        "乐游", "生活时尚", "都市剧场", "欢笑剧场", "游戏风云", "金色学堂", "动漫秀场", "新动漫", "卡酷少儿", "金鹰卡通", "优漫卡通", "哈哈炫动", "嘉佳卡通", 
        "中国交通", "中国天气", "华数4K", "华数星影", "华数动作影院", "华数喜剧影院", "华数家庭影院", "华数经典电影", "华数热播剧场", "华数碟战剧场",
        "华数军旅剧场", "华数城市剧场", "华数武侠剧场", "华数古装剧场", "华数魅力时尚", "华数少儿动画", "华数动画", "iHOT爱喜剧", "iHOT爱科幻", 
        "iHOT爱院线", "iHOT爱悬疑", "iHOT爱历史", "iHOT爱谍战", "iHOT爱旅行", "iHOT爱幼教", "iHOT爱玩具", "iHOT爱体育", "iHOT爱赛车", "iHOT爱浪漫", 
        "iHOT爱奇谈", "iHOT爱科学", "iHOT爱动漫",]}

    CHANNEL_MAPPING = {
    "CCTV1": ["CCTV-1", "CCTV-1 HD", "CCTV1 HD", "CCTV-1综合", "CCTV1 4M1080", "CCTV1 5M1080HEVC"],
    "CCTV2": ["CCTV-2", "CCTV-2 HD", "CCTV2 HD", "CCTV-2财经", "CCTV2 720", "节目暂时不可用 1080"],
    "CCTV3": ["CCTV-3", "CCTV-3 HD", "CCTV3 HD", "CCTV-3综艺", "CCTV3 4M1080"],
    "CCTV4": ["CCTV-4", "CCTV-4 HD", "CCTV4 HD", "CCTV4a", "CCTV4A", "CCTV-4中文国际", "CCTV4 4M1080"],
    "CCTV4欧洲": ["CCTV-4欧洲", "CCTV-4欧洲", "CCTV4欧洲 HD", "CCTV-4 欧洲", "CCTV4o", "CCTV4O", "CCTV-4中文国际欧洲", "CCTV4中文欧洲"],
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
    "CCTV4K": ["CCTV4K超高清", "CCTV-4K超高清", "CCTV-4K 超高清", "CCTV 4K", "CCTV4K超"],
    "CCTV8K": ["CCTV8K超高清", "CCTV-8K超高清", "CCTV-8K 超高清", "CCTV 8K", "CCTV8K超"],
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
    "山东教育卫视": ["山东教育", "山东教育卫视 576"],
    "中国教育1台": ["CETV1", "中国教育一台", "中国教育1", "CETV-1 综合教育", "CETV-1", "中国教育1 576"],
    "中国教育2台": ["CETV2", "中国教育二台", "中国教育2", "CETV-2 空中课堂", "CETV-2", "中国教育2 4M576"],
    "中国教育3台": ["CETV3", "中国教育三台", "中国教育3", "CETV-3 教育服务", "CETV-3"],
    "中国教育4台": ["CETV4", "中国教育四台", "中国教育4", "CETV-4 职业教育", "CETV-4", "中国教育4 4M576"],
    "早期教育": ["中国教育5台", "中国教育5", "中国教育五台", "CETV早期教育", "华电早期教育", "CETV 早期教育", "CETV-5", "CETV5"],
    "CHC动作电影": ["CHC-动作电影"],
    "CHC家庭影院": ["CHC-家庭影院"],
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
    "iHOT爱喜剧": ["iHOT 爱喜剧", "IHOT 爱喜剧", "IHOT爱喜剧", "ihot爱喜剧", "爱喜剧", "ihot 爱喜剧"],
    "iHOT爱科幻": ["iHOT 爱科幻", "IHOT 爱科幻", "IHOT爱科幻", "ihot爱科幻", "爱科幻", "ihot 爱科幻"],
    "iHOT爱院线": ["iHOT 爱院线", "IHOT 爱院线", "IHOT爱院线", "ihot爱院线", "ihot 爱院线", "爱院线"],
    "iHOT爱悬疑": ["iHOT 爱悬疑", "IHOT 爱悬疑", "IHOT爱悬疑", "ihot爱悬疑", "ihot 爱悬疑", "爱悬疑"],
    "iHOT爱历史": ["iHOT 爱历史", "IHOT 爱历史", "IHOT爱历史", "ihot爱历史", "ihot 爱历史", "爱历史"],
    "iHOT爱谍战": ["iHOT 爱谍战", "IHOT 爱谍战", "IHOT爱谍战", "ihot爱谍战", "ihot 爱谍战", "爱谍战"],
    "iHOT爱旅行": ["iHOT 爱旅行", "IHOT 爱旅行", "IHOT爱旅行", "ihot爱旅行", "ihot 爱旅行", "爱旅行"],
    "iHOT爱幼教": ["iHOT 爱幼教", "IHOT 爱幼教", "IHOT爱幼教", "ihot爱幼教", "ihot 爱幼教", "爱幼教"],
    "iHOT爱玩具": ["iHOT 爱玩具", "IHOT 爱玩具", "IHOT爱玩具", "ihot爱玩具", "ihot 爱玩具", "爱玩具"],
    "iHOT爱体育": ["iHOT 爱体育", "IHOT 爱体育", "IHOT爱体育", "ihot爱体育", "ihot 爱体育", "爱体育"],
    "iHOT爱赛车": ["iHOT 爱赛车", "IHOT 爱赛车", "IHOT爱赛车", "ihot爱赛车", "ihot 爱赛车", "爱赛车"],
    "iHOT爱浪漫": ["iHOT 爱浪漫", "IHOT 爱浪漫", "IHOT爱浪漫", "ihot爱浪漫", "ihot 爱浪漫", "爱浪漫"],
    "iHOT爱奇谈": ["iHOT 爱奇谈", "IHOT 爱奇谈", "IHOT爱奇谈", "ihot爱奇谈", "ihot 爱奇谈", "爱奇谈"],
    "iHOT爱科学": ["iHOT 爱科学", "IHOT 爱科学", "IHOT爱科学", "ihot爱科学", "ihot 爱科学", "爱科学"],
    "iHOT爱动漫": ["iHOT 爱动漫", "IHOT 爱动漫", "IHOT爱动漫", "ihot爱动漫", "ihot 爱动漫", "爱动漫"],}

    # 读取第二阶段生成的 zubo.txt
    url_dict = {}
    with open(ZUBO_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ch, url = line.split(",", 1)
            ip_part = url.split("/")[2].split(":")[0]  # 获取 IP
            if ip_part not in url_dict:
                url_dict[ip_part] = []
            url_dict[ip_part].append(line)

    # CCTV1播放性检测，只要能播放，则保留该 IP 下全部频道
    def check_playable(url_line):
        try:
            ch_name, url = url_line.split(",", 1)
            if "CCTV1" in ch_name:
                resp = requests.get(url, timeout=5, stream=True)
                if resp.status_code == 200:
                    return True
        except Exception:
            pass
        return False

    final_url_list = []
    for ip, lines in url_dict.items():
        keep_ip = any(check_playable(line) for line in lines)
        if keep_ip:
            final_url_list.extend(lines)

    # 分类映射（简单示例）
    for line in final_url_list:
        ch, url = line.split(",", 1)
        ch_std = CHANNEL_MAPPING.get(ch, ch)
        final_lines.append(f"{ch_std},{url}")

    # 写入最终 zubo.txt
    with open(ZUBO_FILE, "w", encoding="utf-8") as f:
        for line in final_lines:
            f.write(line + "\n")

    print(f"✅ 第三阶段完成，最终 zubo.txt 共 {len(final_lines)} 条 URL")

    # 推送到仓库
    os.system('git config --global user.name "github-actions"')
    os.system('git config --global user.email "github-actions@users.noreply.github.com"')
    os.system("git add zubo.txt")
    os.system(f'git commit -m "自动更新 zubo.txt（第 {run_count} 次）" || echo "⚠️ 无需提交"')
    os.system("git push origin main")

# 计数=73 时清空 ip 文件并重置计数
elif run_count == 73:
    print("🧹 达到第 73 次，清空 ip 文件并重置计数")
    for ip_file in os.listdir(IP_DIR):
        if ip_file.endswith(".txt"):
            open(os.path.join(IP_DIR, ip_file), "w").close()
    with open(COUNTER_FILE, "w", encoding="utf-8") as f:
        f.write("1")
    print("✅ 已清空 ip 文件夹并重置计数为 1")