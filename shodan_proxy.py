import asyncio
import aiohttp
import re
import datetime
import requests
import time
from urllib.parse import urlparse

# ================= 配置区 =================
SHODAN_API_KEY = "你的_SHODAN_API_KEY"
# 搜索语法：udpxy 且位于中国 (排除酒店干扰)
SHODAN_QUERY = 'product:"udpxy" country:"CN" -hotel -酒店'

# 排除关键词（双重保险，过滤抓取内容中的酒店信息）
EXCLUDE_KEYWORDS = ["酒店", "hotel", "宾馆", "客房", "民宿", "客栈"]

# ================= 核心逻辑 =================

async def get_shodan_ips():
    """从 Shodan API 获取第一页的 100 个节点"""
    print("📡 正在从 Shodan 获取最新 udpxy 节点...")
    api_url = f"https://api.shodan.io/shodan/host/search?key={SHODAN_API_KEY}&query={SHODAN_QUERY}&page=1"
    try:
        # Shodan 频率限制
        await asyncio.sleep(1)
        resp = requests.get(api_url, timeout=15)
        data = resp.json()
        ips = [f"{r['ip_str']}:{r['port']}" for r in data.get('matches', [])]
        print(f"✅ 成功从 Shodan 获取到 {len(ips)} 个原始节点")
        return ips
    except Exception as e:
        print(f"❌ Shodan 访问失败: {e}")
        return []

async def check_alive_and_clean(session, ip_port, semaphore):
    """测速并确保内容不含酒店信息"""
    async with semaphore:
        # 探测 udpxy 的默认状态页
        test_url = f"http://{ip_port}/status"
        start_time = time.time()
        try:
            async with session.get(test_url, timeout=3) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    # 如果状态页包含酒店字样，剔除
                    if any(key in text.lower() for key in EXCLUDE_KEYWORDS):
                        return None
                    
                    latency = int((time.time() - start_time) * 1000)
                    return ip_port, latency
        except:
            pass
        return None

async def get_location_isp(session, ip_port):
    """获取 IP 的省份和运营商"""
    ip = ip_port.split(':')[0]
    api_url = f"http://ip-api.com/json/{ip}?lang=zh-CN"
    try:
        async with session.get(api_url, timeout=5) as resp:
            data = await resp.json()
            if data.get('status') == 'success':
                region = data.get('regionName', '未知省份')
                isp_raw = data.get('isp', '')
                # 标准化运营商名称
                if "Telecom" in isp_raw or "电信" in isp_raw: isp = "电信"
                elif "Unicom" in isp_raw or "联通" in isp_raw: isp = "联通"
                elif "Mobile" in isp_raw or "移动" in isp_raw: isp = "移动"
                else: isp = "其他"
                return f"{region}-{isp}"
    except:
        pass
    return "未知-未知"

# ================= 主程序 =================

async def main():
    semaphore = asyncio.Semaphore(50) # 并发控制
    
    # 1. 获取种子
    raw_nodes = await get_shodan_ips()
    if not raw_nodes: return

    async with aiohttp.ClientSession() as session:
        # 2. 存活验证与内容审计
        print(f"⏳ 正在对 {len(raw_nodes)} 个节点进行可用性测试...")
        tasks = [check_alive_and_clean(session, ip, semaphore) for ip in raw_nodes]
        alive_nodes = [r for r in await asyncio.gather(*tasks) if r]
        
        # 按延迟排序（最流畅的在前）
        alive_nodes.sort(key=lambda x: x[1])
        print(f"✅ 筛选出纯净存活节点: {len(alive_nodes)} 个")

        # 3. 识别省份和运营商
        final_results = []
        for ip_port, latency in alive_nodes:
            info = await get_location_isp(session, ip_port)
            final_results.append(f"{ip_port},{info} ({latency}ms)")
            # 尊重归属地接口的请求频率
            await asyncio.sleep(0.5)

        # 4. 写入 txt 文件
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("ip.txt", "w", encoding="utf-8") as f:
            f.write(f"# 纯净组播代理列表 | 更新时间: {now}\n")
            f.write("# 格式: IP:端口,省份-运营商 (首屏延迟)\n\n")
            for item in final_results:
                f.write(item + "\n")

    print(f"🎉 任务完成，已生成 ip.txt")

if __name__ == "__main__":
    asyncio.run(main())

