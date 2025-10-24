#!/usr/bin/env python3
"""
🎯 tonkiang.us IPTV IP抓取工具
✅ 抓取1-4页IP + 省份分类存储 + 模拟浏览器请求
✅ 自动创建tt文件夹及省份TXT文件
作者：Grok | 2025-10-24
"""

import os
import re
import requests
from bs4 import BeautifulSoup
import logging
from pathlib import Path
from urllib.parse import urljoin

# ===============================
# 🔧 核心配置（可根据需求调整）
CONFIG = {
    "TARGET_DOMAIN": "https://tonkiang.us",  # 目标网站域名
    "PAGE_RANGE": range(1, 5),  # 抓取1-4页（如需调整，如1-3页则改为range(1,4)）
    "OUTPUT_DIR": "tt",  # 输出文件夹名
    "LOG_FILE": "tonkiang_iptv.log",  # 日志文件
    "TIMEOUT": 15,  # 网络请求超时时间（秒）
    # 真实请求头（从抓包数据提取，确保抓取稳定性）
    "HEADERS": {
        ":authority": "tonkiang.us",
        ":method": "GET",
        ":scheme": "https",
        "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "sec-fetch-site": "none",
        "sec-fetch-mode": "navigate",
        "sec-fetch-user": "?1",
        "sec-fetch-dest": "document",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "zh-CN,zh;q=0.9",
        # Cookie从抓包数据提取，若失效需重新更新
        "cookie": "IPTVGO=eb6c67cc; REFERER=Gameover; REFERER2=Game; REFERER1=Over; cf_clearance=6Ya_0Q7hnBoL_Chd.LgkmHyPwIyeO_OkJlREOEqGVDw-1761270271-1.2.1.1-GG1rDyX0BUYytKFPptvP1ukG6Ep4_be48QfvGVVGaRjoVSyOgvoKI1aSTQDYFkZ97r2YTlK5aWxS5hoJgvKldYzMzW.zOxSSNYvte471UDvenZwAAuki2jrjocBA_RpQEoy.hvAeUjy_IYyQ_qGh4.D_W6khDqthvx7EB2GGDCQQ47X6TLxrgTVTi_EbgtUwQ5KkpE7hQNBYaKpTHuic3L9FgX4tFtVTyjEDVQqlCP8"
    }
}

# ===============================
# 📝 日志初始化
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(CONFIG["LOG_FILE"], encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logging.info("✅ 日志系统初始化完成")

# ===============================
# 📂 创建输出文件夹（tt）
def create_output_dir():
    output_dir = Path(CONFIG["OUTPUT_DIR"])
    if not output_dir.exists():
        output_dir.mkdir(parents=True)  # 递归创建文件夹（若父目录不存在也创建）
        logging.info(f"📁 已创建输出文件夹：{output_dir.absolute()}")
    else:
        logging.info(f"📁 输出文件夹已存在：{output_dir.absolute()}")
    return output_dir

# ===============================
# 🌐 抓取单页IPTV数据
def scrape_single_page(page_num, output_dir):
    """抓取指定页码的IPTV数据，并按省份存储"""
    # 构造当前页的请求URL
    page_url = f"{CONFIG['TARGET_DOMAIN']}/iptvmulticast.php?page={page_num}&iphone16=&code="
    logging.info(f"📡 开始抓取第{page_num}页：{page_url}")

    try:
        # 发送GET请求（带真实请求头）
        response = requests.get(
            url=page_url,
            headers=CONFIG["HEADERS"],
            timeout=CONFIG["TIMEOUT"],
            verify=True  # 验证SSL证书（避免安全风险）
        )
        response.raise_for_status()  # 若状态码非200，抛出HTTPError
        soup = BeautifulSoup(response.text, "html.parser")  # 解析HTML

        # 提取所有包含IP的.result容器（目标数据所在区域）
        result_containers = soup.find_all("div", class_="result")
        if not result_containers:
            logging.warning(f"⚠️ 第{page_num}页未找到IP数据容器（.result）")
            return 0

        # 遍历每个.result容器，提取IP和省份信息
        extracted_count = 0
        for container in result_containers:
            # 1. 提取IP地址（从<a>标签的href中匹配IP）
            ip_a_tag = container.find("a", title="Channel List")  # 找到带IP的a标签
            if not ip_a_tag:
                logging.debug(f"⚠️ 跳过无效容器：未找到IP的a标签")
                continue

            ip_match = re.search(r"ip=([\d.]+)", ip_a_tag.get("href", ""))  # 正则匹配IP（如118.121.58.80）
            if not ip_match:
                logging.debug(f"⚠️ 跳过无效a标签：未匹配到IP")
                continue
            ip_address = ip_match.group(1)

            # 2. 提取省份信息（从灰色小字<i>标签中匹配，如“四川省成都市 电信”）
            province_i_tag = container.find("i", style=re.compile(r"font-size: 11px; color: #aaa;"))
            if not province_i_tag:
                logging.debug(f"⚠️ IP {ip_address} 未找到省份信息，标记为「未知省份」")
                province = "未知省份"
            else:
                # 正则匹配省份（如“四川省成都市”“广东省深圳市”，排除“电信”“组播”等后缀）
                province_match = re.search(r"([^省市]+省[^省市]+市|[\w]+省|[\w]+市) [组播|电信|联通|移动]", province_i_tag.text.strip())
                if province_match:
                    province = province_match.group(1)
                else:
                    # 兼容特殊格式（如仅“北京市”“上海市”）
                    province_simple_match = re.search(r"([^上线]+)上线", province_i_tag.text.strip())
                    province = province_simple_match.group(1).strip() if province_simple_match else "未知省份"

            # 3. 提取额外信息（存活天数、上线时间）
            live_days_match = re.search(r"存活<span[^>]+><b>(\d+)</b></span>天", str(container))
            live_days = live_days_match.group(1) if live_days_match else "未知"

            online_time_match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2})上线", province_i_tag.text.strip() if province_i_tag else "")
            online_time = online_time_match.group(1) if online_time_match else "未知"

            # 4. 按省份存储到TXT文件
            province_file = output_dir / f"{province}.txt"  # 构造省份文件路径（如tt/四川省成都市.txt）
            with open(province_file, "a", encoding="utf-8") as f:
                # 写入格式：IP | 上线时间 | 存活天数
                f.write(f"IP: {ip_address} | 上线时间: {online_time} | 存活天数: {live_days}天\n")

            logging.debug(f"✅ 已提取：IP={ip_address} | 省份={province} | 存活={live_days}天 | 上线时间={online_time}")
            extracted_count += 1

        logging.info(f"🎉 第{page_num}页抓取完成：共提取{extracted_count}个IP地址")
        return extracted_count

    except requests.exceptions.HTTPError as e:
        logging.error(f"❌ 第{page_num}页HTTP请求错误：{e}（状态码：{response.status_code}）")
    except requests.exceptions.ConnectionError:
        logging.error(f"❌ 第{page_num}页连接失败：请检查网络或目标网站是否可访问")
    except requests.exceptions.Timeout:
        logging.error(f"❌ 第{page_num}页请求超时：已超过{CONFIG['TIMEOUT']}秒")
    except Exception as e:
        logging.error(f"❌ 第{page_num}页抓取异常：{str(e)}", exc_info=True)  # exc_info=True打印详细堆栈
    return 0

# ===============================
# 🚀 主程序（整合所有流程）
def run_iptv_scraper():
    logging.info("🚀 tonkiang.us IPTV IP抓取工具启动")
    
    # 1. 初始化日志和输出文件夹
    setup_logging()
    output_dir = create_output_dir()

    # 2. 遍历1-4页抓取数据
    total_extracted = 0
    for page in CONFIG["PAGE_RANGE"]:
        page_count = scrape_single_page(page, output_dir)
        total_extracted += page_count

    # 3. 输出最终统计结果
    logging.info(f"🎊 所有页面抓取完成！")
    logging.info(f"📊 统计：共抓取{len(CONFIG['PAGE_RANGE'])}页，累计提取{total_extracted}个IP地址")
    logging.info(f"📁 结果存储路径：{output_dir.absolute()}（按省份分类的TXT文件）")

# ===============================
if __name__ == "__main__":
    run_iptv_scraper()
