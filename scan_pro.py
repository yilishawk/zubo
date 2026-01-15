import asyncio
import aiohttp
import time
import datetime

# ================= 陕西种子池配置 =================
# 格式：(IP种子, 该网段默认端口, 备注)
SEED_CONFIGS = [
    ("113.200.52.216", "8085", "陕西西安-电信"),
    ("36.44.79.26", "5555", "陕西西安-电信"),
    ("36.44.74.221", "5555", "陕西西安-电信"),
    ("1.83.126.64", "4022", "陕西西安-电信"),
    ("124.114.100.78", "6789", "陕西西安-联通"),
    ("1.83.120.195", "8888", "陕西西安-电信")
]

# 备用探测端口（如果默认端口不通，顺便测测这些）
EXTRA_PORTS = ["8012", "8000"]
# ===============================================

async def check_ip_port(session, ip, port, info, semaphore):
    async with semaphore:
        ip_port = f"{ip}:{port}"
        url = f"http://{ip_port}/status"
        try:
            # 超时设为 3 秒，确保跨境访问稳定性
            async with session.get(url, timeout=3) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    if "udpxy" in text.lower():
                        return f"{ip_port},{info}"
        except:
            pass
        return None

async def main():
    print(f"🚀 开始对陕西 {len(SEED_CONFIGS)} 个网段进行并发扫描...")
    start_time = time.time()
    
    tasks_list = []
    for seed_ip, default_port, info in SEED_CONFIGS:
        prefix = ".".join(seed_ip.split('.')[:3])
        # 扫描每个种子所在的 C 段 (1-254)
        for i in range(1, 255):
            target_ip = f"{prefix}.{i}"
            # 探测默认端口
            tasks_list.append((target_ip, default_port, info))
            # 同时也探测一个备用端口，增加中奖率
            # for ep in EXTRA_PORTS:
            #     tasks_list.append((target_ip, ep, info))

    # 并发控制：GitHub Actions 性能可支撑 500 个并发
    semaphore = asyncio.Semaphore(500) 
    async with aiohttp.ClientSession() as session:
        tasks = [check_ip_port(session, ip, port, info, semaphore) for ip, port, info in tasks_list]
        results = [r for r in await asyncio.gather(*tasks) if r]

    # 去重并排序
    results = sorted(list(set(results)))

    # 写入结果
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open("ip.txt", "w", encoding="utf-8") as f:
        f.write(f"# 陕西组播扫描结果 | 更新时间: {now}\n")
        f.write("# 包含网段: 113.200, 36.44, 1.83, 124.114\n\n")
        if not results:
            f.write("# 本次扫描未发现活跃节点，建议检查种子时效性\n")
        for r in results:
            f.write(f"{r}\n")

    print(f"✨ 扫描完成！共探测 {len(tasks_list)} 个点。")
    print(f"✅ 成功找到存活节点: {len(results)} 个。")
    print(f"⏱️ 总耗时: {int(time.time() - start_time)} 秒")

if __name__ == "__main__":
    asyncio.run(main())
