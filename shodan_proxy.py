import asyncio
import aiohttp
import re
import datetime
import requests
import time
import os
from urllib.parse import urlparse

# ================= 配置区 =================
# 建议在 GitHub Secrets 中配置，或者直接填入新 Key
SHODAN_API_KEY = os.getenv("SHODAN_KEY") or "VXmRtHQaSQs41km8zz5E3Mgirecb7Sag"
SHODAN_QUERY = 'product:"udpxy" country:"CN" -hotel -酒店'
EXCLUDE_KEYWORDS = ["酒店", "hotel", "宾馆", "客房", "民宿", "客栈"]

async def get_shodan_ips():
    print("📡 正在从 Shodan 获取最新 udpxy 节点...")
    # 增加校验，防止 Key 为空
    if not SHODAN_API_KEY or len(SHODAN_API_KEY) < 10:
        print("❌ 错误: SHODAN_API_KEY 未设置或格式不正确")
        return []

    api_url = f"https://api.shodan.io/shodan/host/search?key={SHODAN_API_KEY}&query={SHODAN_QUERY}&page=1"
    
    try:
        await asyncio.sleep(2) 
        resp = requests.get(api_url, timeout=15)
        
        # 处理非 200 响应，避免 JSON 解析报错
        if resp.status_code != 200:
            print(f"❌ Shodan API 访问失败，状态码: {resp.status_code}")
            if resp.status_code == 401:
                print("   提示: API Key 可能无效或已过期")
            elif resp.status_code == 403:
                print("   提示: 账户额度不足或被限制")
            return []
            
        data = resp.json()
        matches = data.get('matches', [])
        ips = [f"{r['ip_str']}:{r['port']}" for r in matches]
        print(f"✅ 成功获取到 {len(ips)} 个原始节点")
        return ips
    except Exception as e:
        print(f"❌ 获取 IP 过程中出现异常: {e}")
        return []

async def check_alive_and_clean(session, ip_port, semaphore):
    async with semaphore:
        test_url = f"http://{ip_port}/status"
        start_time = time.time()
        try:
            async with session.get(test_url, timeout=3) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    if any(key in text.lower() for key in EXCLUDE_KEYWORDS):
                        return None
                    latency = int((time.time() - start_time) * 1000)
                    return ip_port, latency
        except:
            pass
        return None

async def get_location_isp(session, ip_port):
    ip = ip_port.split(':')[0]
    # 使用国内可访问的归属地接口或 ip-api
    api_url = f"http://ip-api.com/json/{ip}?lang=zh-CN"
    try:
        async with session.get(api_url, timeout=5) as resp:
            data = await resp.json()
            if data.get('status') == 'success':
                region = data.get('regionName', '未知省份')
                isp_raw = data.get('isp', '')
                if "Telecom" in isp_raw or "电信" in isp_raw: isp = "电信"
                elif "Unicom" in isp_raw or "联通" in isp_raw: isp = "联通"
                elif "Mobile" in isp_raw or "移动" in isp_raw: isp = "移动"
                else: isp = "其他"
                return f"{region}-{isp}"
    except:
        pass
    return "未知-未知"

async def main():
    semaphore = asyncio.Semaphore(50)
    raw_nodes = await get_shodan_ips()
    
    # 如果没抓到 IP，也要确保 ip.txt 存在（哪怕是旧的），防止 Git 报错
    if not raw_nodes:
        if not os.path.exists("ip.txt"):
            with open("ip.txt", "w") as f: f.write("# 暂无数据\n")
        print("⚠️ 未发现新节点，脚本结束")
        return

    async with aiohttp.ClientSession() as session:
        tasks = [check_alive_and_clean(session, ip, semaphore) for ip in raw_nodes]
        alive_nodes = [r for r in await asyncio.gather(*tasks) if r]
        alive_nodes.sort(key=lambda x: x[1])

        final_results = []
        for ip_port, latency in alive_nodes:
            info = await get_location_isp(session, ip_port)
            final_results.append(f"{ip_port},{info} ({latency}ms)")
            await asyncio.sleep(0.5)

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("ip.txt", "w", encoding="utf-8") as f:
            f.write(f"# 纯净组播代理列表 | 更新时间: {now}\n")
            f.write("# 格式: IP:端口,省份-运营商 (延迟)\n\n")
            for item in final_results:
                f.write(item + "\n")

    print(f"🎉 任务完成，生成 {len(final_results)} 个有效 IP")

if __name__ == "__main__":
    asyncio.run(main())
