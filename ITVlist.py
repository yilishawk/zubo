import asyncio
import aiohttp
import re
import datetime
import requests
import eventlet
import os
import threading
eventlet.monkey_patch()

# ===================== 配置 =====================
urls = [
        "http://1.192.12.1:9901",
        "http://1.192.248.1:9901",
        "http://1.194.52.1:10086",
        "http://1.195.111.1:11190",
        "http://1.195.131.1:9901",
        "http://1.195.62.1:9901",
        "http://1.196.192.1:9901",
        "http://1.196.55.1:9901",
        "http://1.197.153.1:9901",
        "http://1.197.203.1:9901",
        "http://1.198.30.1:9901",
        "http://1.198.67.1:9901",
        "http://1.199.234.1:9901",
        "http://1.199.235.1:9901",
        "http://101.65.32.1:9901",
        "http://101.66.199.1:9901",
        "http://101.74.28.1:9901",
        "http://103.39.222.1:9999",
        "http://106.115.121.1:9901",
        "http://106.46.147.1:10443",
        "http://106.46.34.1:9901",
        "http://106.55.164.1:9901",
        "http://110.189.180.1:9901",
        "http://110.52.99.1:9901",
        "http://111.225.114.1:808",
        "http://111.225.115.1:9901",
        "http://111.33.89.1:9901",
        "http://111.59.63.1:9901",
        "http://111.74.155.1:9901",
        "http://111.78.22.1:9901",
        "http://111.78.34.1:9901",
        "http://111.8.224.1:8085",
        "http://111.8.242.1:8085",
        "http://112.123.218.1:9901",
        "http://112.123.219.1:9901",
        "http://112.132.160.1:9901",
        "http://112.193.114.1:9901",
        "http://112.193.42.1:9901",
        "http://112.194.128.1:9901",
        "http://112.194.140.1:9901",
        "http://112.194.206.1:9901",
        "http://112.5.89.1:9900",
        "http://112.5.89.1:9901",
        "http://112.6.117.1:9901",
        "http://112.99.200.1:9901",
        "http://113.100.72.1:9901",
        "http://113.111.104.1:9901",
        "http://113.116.145.1:8883",
        "http://113.116.56.1:8883",
        "http://113.195.4.1:9901",
        "http://113.195.45.1:9901",
        "http://113.195.7.1:9901",
        "http://113.195.8.1:9901",
]

CHANNEL_CATEGORIES = {
    "央视频道": [
        "CCTV1","CCTV2","CCTV3","CCTV4","CCTV4欧洲","CCTV4美洲","CCTV5","CCTV5+","CCTV6","CCTV7",
        "CCTV8","CCTV9","CCTV10","CCTV11","CCTV12","CCTV13","CCTV14","CCTV15","CCTV16","CCTV17","CCTV4K","CCTV8K",
        "兵器科技","风云音乐","风云足球","风云剧场","怀旧剧场","第一剧场","女性时尚","世界地理","央视台球","高尔夫网球",
        "央视文化精品","卫生健康","电视指南","中学生","发现之旅","书法频道","国学频道","环球奇观"
    ],
    "卫视频道": [
        "湖南卫视","浙江卫视","江苏卫视","东方卫视","深圳卫视","北京卫视","广东卫视","广西卫视","东南卫视","海南卫视",
        "河北卫视","河南卫视","湖北卫视","江西卫视","四川卫视","重庆卫视","贵州卫视","云南卫视","天津卫视","安徽卫视",
        "山东卫视","辽宁卫视","黑龙江卫视","吉林卫视","内蒙古卫视","宁夏卫视","山西卫视","陕西卫视","甘肃卫视","青海卫视",
        "新疆卫视","西藏卫视","三沙卫视","兵团卫视","延边卫视","安多卫视","康巴卫视","农林卫视","山东教育卫视",
        "中国教育1台","中国教育2台","中国教育3台","中国教育4台","早期教育"
    ],
}

CHANNEL_MAPPING = {
    "CCTV1": ["CCTV1综合","央视1台","CCTV-1"],
    "CCTV2": ["CCTV2财经","央视2台","CCTV-2"],
    "CCTV3": ["CCTV3综艺","央视3台","CCTV-3"],
    "CCTV4": ["CCTV4国际","CCTV4中文国际"],
    "CCTV5": ["CCTV5体育","CCTV5"],
    "CCTV5+": ["CCTV5+体育","CCTV5+"],
    "CCTV6": ["CCTV6电影","央视6台"],
    "CCTV7": ["CCTV7农业军事","央视7台"],
    # 其他可按需添加
}

RESULTS_PER_CHANNEL = 5  # 每个频道保留源数
# ==============================================

# 修改 URL，循环 C 段 1-255
async def generate_urls(url):
    modified_urls = []
    ip_start = url.find("//")+2
    ip_end = url.find(":", ip_start)
    base = url[:ip_start]
    ip_prefix = url[ip_start:ip_end].rsplit('.',1)[0]  # 去掉最后一段
    port = url[ip_end:]
    for i in range(1,256):
        modified_urls.append(f"{base}{ip_prefix}.{i}{port}/iptv/live/1000.json?key=txiptv")
    return modified_urls

async def fetch_json(session, url, semaphore):
    async with semaphore:
        try:
            async with session.get(url, timeout=0.5) as resp:
                data = await resp.json()
                results = []
                for item in data.get('data', []):
                    name = item.get('name')
                    urlx = item.get('url')
                    if not name or not urlx or ',' in urlx:
                        continue
                    if not urlx.startswith("http"):
                        base = url.split("/iptv")[0]
                        urlx = base + urlx
                    # 映射标准名
                    for std_name, aliases in CHANNEL_MAPPING.items():
                        if name in aliases:
                            name = std_name
                            break
                    results.append((name,urlx))
                return results
        except:
            return []

async def check_url(session, url, semaphore):
    async with semaphore:
        try:
            async with session.get(url, timeout=0.5) as resp:
                if resp.status == 200:
                    return url
        except:
            return None

async def main():
    semaphore = asyncio.Semaphore(500)
    async with aiohttp.ClientSession() as session:
        # 生成 URL
        all_urls = []
        for url in urls:
            modified_urls = await generate_urls(url)
            all_urls.extend(modified_urls)

        # 检查可用 URL
        tasks = [check_url(session, u, semaphore) for u in all_urls]
        valid_urls = [r for r in await asyncio.gather(*tasks) if r]

        # 抓取节目单
        tasks = [fetch_json(session, u, semaphore) for u in valid_urls]
        results = []
        for sublist in await asyncio.gather(*tasks):
            results.extend(sublist)

    final_results = [(name, url, 0) for name, url in results]

    # ================== 分类 ==================
    itv_dict = {cat: [] for cat in CHANNEL_CATEGORIES}

    for name, url, speed in final_results:
        for cat, channels in CHANNEL_CATEGORIES.items():
            if name in channels:
                itv_dict[cat].append((name, url, speed))
                break

    # ================== 输出 itvlist.txt ==================
with open("itvlist.txt", 'w', encoding='utf-8') as f:
    for cat in CHANNEL_CATEGORIES:
        f.write(f"{cat},#genre#\n")

        for ch in CHANNEL_CATEGORIES[cat]:
            ch_items = [x for x in itv_dict[cat] if x[0] == ch]

            ch_items = ch_items[:RESULTS_PER_CHANNEL]

            for item in ch_items:
                f.write(f"{item[0]},{item[1]}\n")

if __name__=="__main__":
    asyncio.run(main())