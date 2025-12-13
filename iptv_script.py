#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import aiohttp
import time
from urllib.parse import urljoin
import logging
from aiohttp import web

# ---------------- 默认配置 ----------------
URL_FILE = "https://raw.githubusercontent.com/kakaxi-1/zubo/main/ip_urls.txt"
RESULTS_PER_CHANNEL = 3
FETCH_INTERVAL = 21600  # 秒，6小时
EPG_URL = "https://kakaxi-1.asia/epg.xml"
LOGO_BASE = "https://kakaxi-1.asia/LOGO/"

CHANNEL_MAPPING = {
    "CCTV1": ["CCTV1", "央视一套"],
    "CCTV2": ["CCTV2", "央视二套"],
    "CCTV3": ["CCTV3", "央视三套"],
}

CHANNEL_CATEGORIES = {
    "央视": ["CCTV1", "CCTV2", "CCTV3"],
    "地方": ["BTV1", "BTV2"]
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger()

# ---------------- 核心函数 ----------------
def load_urls():
    import requests
    try:
        resp = requests.get(URL_FILE, timeout=5)
        resp.raise_for_status()
        urls = [line.strip() for line in resp.text.splitlines() if line.strip()]
        log.info(f"📡 已加载 {len(urls)} 个基础 URL")
        return urls
    except Exception as e:
        log.error(f"❌ 下载 {URL_FILE} 失败: {e}")
        return []

async def generate_urls(url):
    modified_urls = []
    ip_start = url.find("//") + 2
    ip_end = url.find(":", ip_start)
    base = url[:ip_start]
    ip_prefix = url[ip_start:ip_end].rsplit('.', 1)[0]
    port = url[ip_end:]
    json_paths = [
        "/iptv/live/1000.json?key=txiptv",
        "/iptv/live/1001.json?key=txiptv",
        "/live/channels.json",
        "/iptv/live.json",
    ]
    for i in range(1, 256):
        ip = f"{base}{ip_prefix}.{i}{port}"
        for path in json_paths:
            modified_urls.append(f"{ip}{path}")
    return modified_urls

async def check_url(session, url, semaphore):
    async with semaphore:
        try:
            async with session.get(url, timeout=1) as resp:
                if resp.status == 200:
                    return url
        except:
            return None

async def fetch_json(session, url, semaphore):
    async with semaphore:
        try:
            async with session.get(url, timeout=2) as resp:
                data = await resp.json()
                results = []
                for item in data.get('data', []):
                    name = item.get('name')
                    urlx = item.get('url')
                    if not name or not urlx or ',' in urlx:
                        continue
                    if not urlx.startswith("http"):
                        urlx = urljoin(url, urlx)
                    for std_name, aliases in CHANNEL_MAPPING.items():
                        if name in aliases:
                            name = std_name
                            break
                    results.append((name, urlx))
                return results
        except:
            return []

async def measure_speed(session, url, semaphore):
    async with semaphore:
        start = time.time()
        try:
            async with session.head(url, timeout=2) as resp:
                if resp.status == 200:
                    return int((time.time() - start) * 1000)
                return 999999
        except:
            return 999999

def is_valid_stream(url):
    if url.startswith(("rtp://", "udp://", "rtsp://")): return False
    if "239." in url: return False
    if url.startswith(("http://16.", "http://10.", "http://192.168.")): return False
    if "/paiptv/" in url or "/00/SNM/" in url or "/00/CHANNEL" in url: return False
    return url.startswith("http") and any(url.endswith(ext) for ext in [".m3u8", ".ts", ".flv", ".mp4", ".mkv"])

# ---------------- IPTV抓取 ----------------
itv_dict_global = {}

async def fetch_itvlist():
    global itv_dict_global
    while True:
        try:
            log.info("🚀 开始抓取 IPTV 列表")
            semaphore = asyncio.Semaphore(150)
            urls = load_urls()
            if not urls:
                log.warning("⚠️ 没有可用 URL，等待下次抓取")
                await asyncio.sleep(FETCH_INTERVAL)
                continue

            async with aiohttp.ClientSession() as session:
                all_urls = []
                for url in urls:
                    modified_urls = await generate_urls(url)
                    all_urls.extend(modified_urls)

                tasks = [check_url(session, u, semaphore) for u in all_urls]
                valid_urls = [r for r in await asyncio.gather(*tasks) if r]

                tasks = [fetch_json(session, u, semaphore) for u in valid_urls]
                results = []
                fetched = await asyncio.gather(*tasks)
                for sublist in fetched:
                    results.extend(sublist)

                final_results = [(name, url) for name, url in results if is_valid_stream(url)]

                # 测速排序
                speed_tasks = [measure_speed(session, url, asyncio.Semaphore(150)) for _, url in final_results]
                speeds = await asyncio.gather(*speed_tasks)
                final_results = [(name, url, speed) for (name, url), speed in zip(final_results, speeds)]
                final_results.sort(key=lambda x: x[2])

                # 分类存储
                itv_dict = {cat: [] for cat in CHANNEL_CATEGORIES}
                for name, url, _ in final_results:
                    for cat, channels in CHANNEL_CATEGORIES.items():
                        if name in channels:
                            itv_dict[cat].append((name, url))
                            break

                itv_dict_global = itv_dict
                log.info("🎉 M3U 列表已更新")
        except Exception as e:
            log.error(f"❌ 抓取失败: {e}")
        await asyncio.sleep(FETCH_INTERVAL)

# ---------------- HTTP 服务 ----------------
async def handle_m3u(request):
    try:
        lines = [f'#EXTM3U x-tvg-url="{EPG_URL}"\n']
        for cat, channels in itv_dict_global.items():
            for name, url in channels[:RESULTS_PER_CHANNEL]:
                logo = f"{LOGO_BASE}{name}.png"
                lines.append(f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="{cat}",{name}\n{url}\n')
        return web.Response(text="".join(lines), content_type='application/vnd.apple.mpegurl')
    except Exception as e:
        return web.Response(text=f"Error: {e}", status=500)

async def start_server():
    app = web.Application()
    app.router.add_get("/m3u", handle_m3u)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 9090)
    await site.start()
    log.info("🌐 HTTP 服务已启动，端口 9090，访问 /m3u 获取 M3U")

# ---------------- 主程序 ----------------
async def main():
    await asyncio.gather(
        fetch_itvlist(),
        start_server()
    )

if __name__ == "__main__":
    asyncio.run(main())
