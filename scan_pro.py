import asyncio
import aiohttp
import time
import datetime

# ================= 配置区 =================
SEED_IP = "36.46.98.221"
# 定义你想探测的端口列表（根据经验，udpxy 常用这几个）
PORTS = ["8012", "8000", "8888", "4022"] 
INFO = "陕西西安-电信"
# ==========================================

async def check_ip_port(session, ip, port, semaphore):
    async with semaphore:
        ip_port = f"{ip}:{port}"
        url = f"http://{ip_port}/status"
        try:
            # 缩短超时到 1.5 秒，因为我们要扫 IP x 端口，数量翻倍了
            async with session.get(url, timeout=1.5) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    if "udpxy" in text.lower():
                        return ip_port
        except:
            pass
        return None

async def main():
    print(f"🚀 开始深度扫描 {INFO} (包含端口: {', '.join(PORTS)})...")
    start_time = time.time()
    
    prefix = ".".join(SEED_IP.split('.')[:3])
    
    # 组合 IP 和 端口： 254个IP * 4个端口 = 1016 个任务
    tasks_list = []
    for i in range(1, 255):
        ip = f"{prefix}.{i}"
        for port in PORTS:
            tasks_list.append((ip, port))
    
    # GitHub Actions 性能强劲，并发开到 300 没问题
    semaphore = asyncio.Semaphore(300) 
    async with aiohttp.ClientSession() as session:
        tasks = [check_ip_port(session, ip, port, semaphore) for ip, port in tasks_list]
        results = [r for r in await asyncio.gather(*tasks) if r]

    # 去重并排序
    results = sorted(list(set(results)))

    # 写入结果
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open("ip.txt", "w", encoding="utf-8") as f:
        f.write(f"# 深度扫描: {INFO} | 更新时间: {now}\n")
        for r in results:
            f.write(f"{r},{INFO}\n")

    print(f"✨ 扫描完成！共探测 {len(tasks_list)} 个点，找到 {len(results)} 个活跃节点。")
    print(f"⏱️ 总耗时: {int(time.time() - start_time)} 秒")

if __name__ == "__main__":
    asyncio.run(main())
