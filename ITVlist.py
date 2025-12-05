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
        "http://1.197.153.1:9901",
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