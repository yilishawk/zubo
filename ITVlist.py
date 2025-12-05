import asyncio
import aiohttp
import re
import datetime
import requests
import eventlet
import os
import threading
eventlet.monkey_patch()

# ------------------ 配置 ------------------
CHANNEL_CATEGORIES = {
    "央视频道": [
        "CCTV1", "CCTV2", "CCTV3", "CCTV4", "CCTV4欧洲", "CCTV4美洲", "CCTV5", "CCTV5+", "CCTV6", "CCTV7",
        "CCTV8", "CCTV9", "CCTV10", "CCTV11", "CCTV12", "CCTV13", "CCTV14", "CCTV15", "CCTV16", "CCTV17",
        "CCTV4K", "CCTV8K", "兵器科技", "风云音乐", "风云足球", "风云剧场", "怀旧剧场", "第一剧场",
        "女性时尚", "世界地理", "央视台球", "高尔夫网球", "央视文化精品", "卫生健康", "电视指南",
        "中学生", "发现之旅", "书法频道", "国学频道", "环球奇观"
    ],
    "卫视频道": [
        "湖南卫视", "浙江卫视", "江苏卫视", "东方卫视", "深圳卫视", "北京卫视", "广东卫视", "广西卫视",
        "东南卫视", "海南卫视", "河北卫视", "河南卫视", "湖北卫视", "江西卫视", "四川卫视", "重庆卫视",
        "贵州卫视", "云南卫视", "天津卫视", "安徽卫视", "山东卫视", "辽宁卫视", "黑龙江卫视", "吉林卫视",
        "内蒙古卫视", "宁夏卫视", "山西卫视", "陕西卫视", "甘肃卫视", "青海卫视", "新疆卫视", "西藏卫视",
        "三沙卫视", "兵团卫视", "延边卫视", "安多卫视", "康巴卫视", "农林卫视", "山东教育卫视",
        "中国教育1台", "中国教育2台", "中国教育3台", "中国教育4台", "早期教育"
    ]
}

CHANNEL_MAPPING = {
    "CCTV1": ["CCTV1综合", "央视1台", "CCTV-1"],
    "CCTV2": ["CCTV2财经", "央视2台", "CCTV-2"],
    "CCTV3": ["CCTV3综艺", "央视3台", "CCTV-3"],
    "CCTV4": ["CCTV4国际", "CCTV4中文国际"],
    "CCTV5+": ["CCTV5+体育", "CCTV5+"],
    # 可继续补充映射
}

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
        "http://61.138.128.1:19901",
        "http://61.136.67.1:50085",
        "http://61.136.172.1:9901",
        "http://61.130.72.1:8888",
]

# ------------------ 异步检查接口 ------------------
async def modify_urls(url):
    modified_urls = []
    ip_start_index = url.find("//") + 2
    ip_end_index = url.find(":", ip_start_index)
    base_url = url[:ip_start_index]
    ip_address = url[ip_start_index:ip_end_index]
    port = url[ip_end_index:]
    ip_end = "/iptv/live/1000.json?key=txiptv"
    for i in range(1, 256):
        modified_ip = f"{ip_address[:-1]}{i}"
        modified_url = f"{base_url}{modified_ip}{port}{ip_end}"
        modified_urls.append(modified_url)
    return modified_urls

async def is_url_accessible(session, url, semaphore):
    async with semaphore:
        try:
            async with session.get(url, timeout=0.5) as response:
                if response.status == 200:
                    return url
        except:
            pass
    return None

async def check_urls(session, urls, semaphore):
    tasks = []
    for url in urls:
        url = url.strip()
        modified_urls = await modify_urls(url)
        for modified_url in modified_urls:
            task = asyncio.create_task(is_url_accessible(session, modified_url, semaphore))
            tasks.append(task)
    results = await asyncio.gather(*tasks)
    return [r for r in results if r]

# ------------------ 抓取 JSON ------------------
async def fetch_json(session, url, semaphore):
    async with semaphore:
        try:
            async with session.get(url, timeout=0.5) as response:
                json_data = await response.json()
                results = []
                for item in json_data.get('data', []):
                    if isinstance(item, dict):
                        name = item.get('name')
                        urlx = item.get('url')
                        if not name or not urlx or ',' in urlx:
                            continue
                        if not urlx.startswith('http'):
                            ip_start_index = url.find("//") + 2
                            ip_end_index = url.find("/", ip_start_index)
                            urlx = url[:ip_end_index] + urlx
                        for std_name, aliases in CHANNEL_MAPPING.items():
                            if name in aliases:
                                name = std_name
                                break
                        results.append((name, urlx))
                return results
        except:
            return []

# ------------------ 测速 ------------------
def check_channel_speed(channel_name, channel_url):
    try:
        ts_lines = requests.get(channel_url, timeout=1).text.strip().split('\n')
        ts_files = [line for line in ts_lines if not line.startswith('#')]
        if not ts_files:
            return None
        ts_url = channel_url.rsplit('/', 1)[0] + '/' + ts_files[0]
        start = datetime.datetime.now().timestamp()
        content = requests.get(ts_url, timeout=2).content
        end = datetime.datetime.now().timestamp()
        speed = len(content) / max((end - start), 0.001) / 1024 / 1024  # MB/s
        if speed > 0:
            return (channel_name, channel_url, round(speed, 3))
    except:
        return None

# ------------------ 主逻辑 ------------------
async def main():
    semaphore = asyncio.Semaphore(500)
    async with aiohttp.ClientSession() as session:
        valid_urls = await check_urls(session, urls, semaphore)
        all_results = []
        tasks = [asyncio.create_task(fetch_json(session, url, semaphore)) for url in valid_urls]
        results_list = await asyncio.gather(*tasks)
        for sublist in results_list:
            all_results.extend(sublist)

    # CCTV1 不可用时回退测试第一个频道
    cctv1_list = [r for r in all_results if r[0] == 'CCTV1']
    if not cctv1_list and all_results:
        test_result = check_channel_speed(*all_results[0])
        if test_result:
            all_results = [r for r in all_results if check_channel_speed(r[0], r[1])]

    # 多线程测速
    task_queue = eventlet.Queue()
    results = []
    error_channels = []

    def worker():
        while True:
            item = task_queue.get()
            if not item:
                task_queue.task_done()
                break
            channel_name, channel_url = item
            res = check_channel_speed(channel_name, channel_url)
            if res:
                results.append(res)
            else:
                error_channels.append((channel_name, channel_url))
            task_queue.task_done()

    num_workers = 10
    for _ in range(num_workers):
        t = threading.Thread(target=worker, daemon=True)
        t.start()

    for r in all_results:
        task_queue.put(r)
    for _ in range(num_workers):
        task_queue.put(None)

    task_queue.join()

    max_per_channel = 5
    final_dict = {cat: {} for cat in CHANNEL_CATEGORIES}
    for cat_name, channels in CHANNEL_CATEGORIES.items():
        for ch in channels:
            ch_results = [r for r in results if r[0] == ch][:max_per_channel]
            if ch_results:
                final_dict[cat_name][ch] = ch_results

    # 生成 itvlist.txt
    with open("itvlist.txt", 'w', encoding='utf-8') as f:
        for cat_name in CHANNEL_CATEGORIES:
            f.write(f"{cat_name},#genre#\n")
            for ch_name in CHANNEL_CATEGORIES[cat_name]:
                for entry in final_dict[cat_name].get(ch_name, []):
                    f.write(f"{entry[0]},{entry[1]}\n")

if __name__ == "__main__":
    asyncio.run(main())