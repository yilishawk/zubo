import asyncio
import aiohttp
import datetime
import threading
import os
import time
from flask import Flask, send_file, Response
from urllib.parse import urljoin

# ================= 配置 =================
PORT = 5000
OUTPUT_FILE = "itvlist.txt"
UPDATE_INTERVAL = 6 * 60 * 60  # 每 6 小时更新一次
CONCURRENCY = 80
RESULTS_PER_CHANNEL = 10

BASE_URLS = [
    "http://1.192.12.1:9901",
    "http://1.192.248.1:9901",
    "http://61.54.14.1:9901",
]

JSON_PATHS = [
    "/iptv/live/1000.json?key=txiptv",
    "/iptv/live/1001.json?key=txiptv",
    "/iptv/live.json",
    "/live/channels.json",
]

CHANNEL_CATEGORIES = {
    "央视频道": ["CCTV1", "CCTV2"],
    "卫视频道": ["湖南卫视", "浙江卫视"],
}

CHANNEL_MAPPING = {
    "CCTV1": ["CCTV-1", "CCTV1HD", "CCTV-1 综合"],
    "CCTV2": ["CCTV-2", "CCTV2HD", "CCTV-2 财经"],
}

# ================= Flask 服务 =================
app = Flask(__name__)

@app.route("/list.txt")
def serve_list():
    if not os.path.exists(OUTPUT_FILE):
        return Response("节目单生成中，请稍候...\n", mimetype="text/plain")
    return send_file(OUTPUT_FILE, mimetype="text/plain")

# ================= IPTV 逻辑 =================
def is_valid_stream(url):
    if not url.startswith("http"):
        return False
    if any(bad in url for bad in ("239.", "/paiptv/", "/00/SNM/")):
        return False
    return any(ext in url for ext in (".m3u8", ".ts", ".flv", ".mp4"))

async def generate_urls(base):
    ip_start = base.find("//") + 2
    ip_end = base.find(":", ip_start)
    base_url = base[:ip_start]
    prefix = base[ip_start:ip_end].rsplit(".", 1)[0]
    port = base[ip_end:]

    urls = []
    for i in range(1, 256):
        for path in JSON_PATHS:
            urls.append(f"{base_url}{prefix}.{i}{port}{path}")
    return urls

async def check_json(session, url, sem):
    async with sem:
        try:
            async with session.get(url, timeout=1) as r:
                return url if r.status == 200 else None
        except:
            return None

async def fetch_channels(session, url, sem):
    async with sem:
        try:
            async with session.get(url, timeout=2) as r:
                data = await r.json()
                results = []
                for item in data.get("data", []):
                    name = item.get("name")
                    u = item.get("url")
                    if not name or not u or "," in u:
                        continue
                    if not u.startswith("http"):
                        u = urljoin(url, u)

                    for std, aliases in CHANNEL_MAPPING.items():
                        if name in aliases:
                            name = std

                    if is_valid_stream(u):
                        results.append((name, u))
                return results
        except:
            return []

async def measure_speed(session, url, sem):
    async with sem:
        start = time.time()
        try:
            async with session.head(url, timeout=2) as resp:
                if resp.status == 200:
                    return int((time.time() - start) * 1000)
                return 999999
        except:
            return 999999

async def generate_itvlist():
    sem = asyncio.Semaphore(CONCURRENCY)
    async with aiohttp.ClientSession() as session:
        all_urls = []
        for base in BASE_URLS:
            all_urls.extend(await generate_urls(base))

        checked = await asyncio.gather(*[check_json(session, u, sem) for u in all_urls])
        valid_jsons = [u for u in checked if u]

        channels = []
        fetched = await asyncio.gather(*[fetch_channels(session, u, sem) for u in valid_jsons])
        for sub in fetched:
            channels.extend(sub)

        speed_tasks = [measure_speed(session, url, sem) for _, url in channels]
        speeds = await asyncio.gather(*speed_tasks)

        channels_with_speed = [(name, url, spd) for (name, url), spd in zip(channels, speeds)]

        grouped = {k: [] for k in CHANNEL_CATEGORIES}
        for name, url, speed in channels_with_speed:
            for cat, names in CHANNEL_CATEGORIES.items():
                if name in names:
                    grouped[cat].append((name, url, speed))

        for cat in grouped:
            grouped[cat].sort(key=lambda x: x[2])  # 速度快的在前

        write_itvlist(grouped)

def write_itvlist(grouped):
    now = datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=8))
    ).strftime("%Y-%m-%d %H:%M:%S")

    tmp_file = OUTPUT_FILE + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        f.write("更新时间,#genre#\n")
        f.write(f"{now},http://example.com/disclaimer.mp4\n\n")

        for cat in CHANNEL_CATEGORIES:
            f.write(f"{cat},#genre#\n")
            for name, url, _ in grouped[cat][:RESULTS_PER_CHANNEL]:
                f.write(f"{name},{url}\n")

    os.replace(tmp_file, OUTPUT_FILE)

def background_loop():
    """首次生成 + 周期性循环更新"""
    asyncio.run(generate_itvlist())
    while True:
        time.sleep(UPDATE_INTERVAL)
        try:
            asyncio.run(generate_itvlist())
        except Exception as e:
            print(f"后台更新出错: {e}")

if __name__ == "__main__":
    threading.Thread(target=background_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT)