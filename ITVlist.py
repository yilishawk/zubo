import asyncio
import aiohttp
import datetime

CHANNEL_CATEGORIES = {
    "央视频道": ["CCTV1", "CCTV2", "CCTV3", "CCTV4", "CCTV5", "CCTV5+"],
    "卫视频道": ["湖南卫视", "浙江卫视", "江苏卫视"]
}

CHANNEL_MAPPING = {
    "CCTV1": ["CCTV-1", "CCTV-1 HD", "CCTV1 HD", "CCTV-1综合"],
    "CCTV2": ["CCTV-2", "CCTV-2 HD", "CCTV2 HD", "CCTV-2财经"],
    "CCTV3": ["CCTV-3", "CCTV-3 HD", "CCTV3 HD", "CCTV-3综艺"],
    "CCTV4": ["CCTV-4", "CCTV-4国际", "CCTV-4中文国际"],
    "CCTV5": ["CCTV-5", "CCTV-5 体育"],
    "CCTV5+": ["CCTV-5+", "CCTV-5+ 体育"],
}

MAX_SOURCES = 6
CHECK_TIMEOUT = 2
CONCURRENT_LIMIT = 20

async def fetch_json(session, url):
    try:
        async with session.get(url, timeout=0.5) as response:
            data = await response.json()
            results = []
            for item in data.get('data', []):
                if not isinstance(item, dict):
                    continue
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

async def check_cctv1_playable(session, urls):
    semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)
    async def check(url):
        async with semaphore:
            try:
                async with session.get(url, timeout=CHECK_TIMEOUT) as resp:
                    return resp.status == 200
            except:
                return False
    tasks = [asyncio.create_task(check(u)) for u in urls]
    results = await asyncio.gather(*tasks)
    return any(results), results.count(True), results.count(False)

async def main():
    # ------------------------
    # 将 urls 放在这里定义
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
        "http://183.131.246.1:9901",
]
    # ------------------------

    all_results = []
    async with aiohttp.ClientSession() as session:
        for url in urls:
            modified_url = f"{url}/iptv/live/1000.json?key=txiptv"
            batch_results = await fetch_json(session, modified_url)
            cctv1_urls = [u for n, u in batch_results if n == "CCTV1"]
            if cctv1_urls:
                playable, good_count, bad_count = await check_cctv1_playable(session, cctv1_urls)
                print(f"{datetime.datetime.now()} 批次 {url} CCTV1可用: {playable}, 可用源: {good_count}, 不可用源: {bad_count}, 总源数: {len(cctv1_urls)}")
                if playable:
                    all_results.extend(batch_results)
                else:
                    print(f"{datetime.datetime.now()} CCTV1 不可用，跳过该批次 {url}")
            else:
                print(f"{datetime.datetime.now()} 批次 {url} 无CCTV1源，跳过")

    # 按分类顺序整理结果
    final_results = []
    for category, names in CHANNEL_CATEGORIES.items():
        counters = {}
        for name in names:
            for ch_name, ch_url in all_results:
                if ch_name == name:
                    if ch_name in counters:
                        if counters[ch_name] >= MAX_SOURCES:
                            continue
                        counters[ch_name] += 1
                    else:
                        counters[ch_name] = 1
                    final_results.append((ch_name, ch_url, category))

    # 输出
    with open("itvlist.txt", "w", encoding="utf-8") as f:
        for category, names in CHANNEL_CATEGORIES.items():
            f.write(f"{category},#genre#\n")
            for name in names:
                for ch_name, ch_url, ch_cat in final_results:
                    if ch_name == name:
                        f.write(f"{ch_name},{ch_url}\n")

    print(f"\n总可用频道数: {len(final_results)}")

if __name__ == "__main__":
    asyncio.run(main())