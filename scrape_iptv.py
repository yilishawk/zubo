import requests
import re
import os
import time
import sys
import cloudscraper
from bs4 import BeautifulSoup

def scrape_tonkiang():
    base_url = "https://tonkiang.us/iptvmulticast.php"
    
    # 方法1: 使用 cloudscraper 绕过 Cloudflare
    print("🚀 尝试使用 cloudscraper 绕过 Cloudflare...")
    
    try:
        # 创建 cloudscraper 实例
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
        
        # 测试连接
        test_response = scraper.get("https://tonkiang.us/", timeout=30)
        print(f"测试连接状态码: {test_response.status_code}")
        
        if test_response.status_code == 200:
            print("✅ cloudscraper 连接成功，使用此方法")
            return scrape_with_cloudscraper(scraper)
        else:
            print(f"❌ cloudscraper 测试失败，状态码: {test_response.status_code}")
            raise Exception("Cloudscraper failed")
            
    except Exception as e:
        print(f"❌ cloudscraper 方法失败: {e}")
        print("🔄 回退到普通 requests 方法...")
        return scrape_with_requests()

def scrape_with_cloudscraper(scraper):
    """使用 cloudscraper 进行抓取"""
    output_dir = "tonkiang"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    all_ips_by_province = {}
    total_ips = 0
    
    print("🚀 开始抓取IPTV IP地址...")
    
    for page in range(1, 5):
        print(f"\n📄 正在抓取第 {page} 页...")
        
        url = f"https://tonkiang.us/iptvmulticast.php?page={page}&iphone16=&code="
        print(f"请求URL: {url}")
        
        try:
            response = scraper.get(url, timeout=30)
            print(f"响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                # 检查是否是挑战页面
                if "Checking your browser" in response.text or "cloudflare" in response.text.lower():
                    print("❌ 被Cloudflare挑战阻止")
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                ips_found = parse_page(soup, all_ips_by_province)
                total_ips += ips_found
                print(f"  📊 第 {page} 页找到 {ips_found} 个IP")
                
            else:
                print(f"  ❌ 第 {page} 页请求失败，状态码: {response.status_code}")
            
            time.sleep(3)  # 更长的延迟
            
        except Exception as e:
            print(f"  ❌ 第 {page} 页处理异常: {e}")
            continue
    
    return save_results(all_ips_by_province, total_ips)

def scrape_with_requests():
    """使用普通 requests 进行抓取（备用方法）"""
    output_dir = "tonkiang"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    all_ips_by_province = {}
    total_ips = 0
    
    print("🔄 使用普通 requests 方法...")
    
    # 使用更真实的浏览器头信息
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        'Cache-Control': 'max-age=0',
    }
    
    # 创建会话
    session = requests.Session()
    session.headers.update(headers)
    
    for page in range(1, 5):
        print(f"\n📄 正在抓取第 {page} 页...")
        
        url = f"https://tonkiang.us/iptvmulticast.php?page={page}&iphone16=&code="
        
        try:
            response = session.get(url, timeout=15)
            print(f"响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                ips_found = parse_page(soup, all_ips_by_province)
                total_ips += ips_found
                print(f"  📊 第 {page} 页找到 {ips_found} 个IP")
            else:
                print(f"  ❌ 第 {page} 页请求失败")
            
            time.sleep(2)
            
        except Exception as e:
            print(f"  ❌ 第 {page} 页处理异常: {e}")
            continue
    
    return save_results(all_ips_by_province, total_ips)

def parse_page(soup, all_ips_by_province):
    """解析页面内容，提取IP和省份信息"""
    ips_found = 0
    
    # 查找所有的result div
    result_divs = soup.find_all('div', class_='result')
    
    for result in result_divs:
        # 提取IP地址
        ip = extract_ip(result)
        if ip:
            # 提取省份信息
            province = extract_province(result)
            
            # 将IP添加到对应省份的列表中
            if province not in all_ips_by_province:
                all_ips_by_province[province] = []
            all_ips_by_province[province].append(ip)
            ips_found += 1
            print(f"  ✅ 找到IP: {ip} - 省份: {province}")
    
    return ips_found

def extract_ip(result):
    """从result div中提取IP地址"""
    # 多种方法尝试提取IP
    ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    
    # 方法1: 从channel div中提取
    channel_div = result.find('div', class_='channel')
    if channel_div:
        text = channel_div.get_text()
        ip_matches = re.findall(ip_pattern, text)
        if ip_matches:
            return ip_matches[0]
    
    # 方法2: 从链接中提取
    links = result.find_all('a')
    for link in links:
        href = link.get('href', '')
        text = link.get_text()
        # 从href中提取
        ip_matches = re.findall(ip_pattern, href)
        if ip_matches:
            return ip_matches[0]
        # 从文本中提取
        ip_matches = re.findall(ip_pattern, text)
        if ip_matches:
            return ip_matches[0]
    
    # 方法3: 从整个div中提取
    text = result.get_text()
    ip_matches = re.findall(ip_pattern, text)
    if ip_matches:
        return ip_matches[0]
    
    return None

def extract_province(result):
    """从result div中提取省份信息"""
    location_divs = result.find_all('div', style=re.compile(r'font-size: 11px; color: #aaa;'))
    for location_div in location_divs:
        text = location_div.get_text()
        # 提取省份信息
        province_matches = re.findall(r'([\u4e00-\u9fa5]{2,6}省|[\u4e00-\u9fa5]{2,4}市|[\u4e00-\u9fa5]{2,6}自治区)', text)
        if province_matches:
            return province_matches[0]
    
    return "其他"

def save_results(all_ips_by_province, total_ips):
    """保存结果到文件"""
    output_dir = "tonkiang"
    files_created = 0
    
    print(f"\n📈 抓取统计:")
    print(f"  总IP数量: {total_ips}")
    print(f"  省份数量: {len(all_ips_by_province)}")
    
    for province, ips in all_ips_by_province.items():
        # 清理文件名
        safe_filename = re.sub(r'[<>:"/\\|?*]', '', province)
        file_path = os.path.join(output_dir, f"{safe_filename}.txt")
        
        # 去重并写入文件
        unique_ips = list(set(ips))
        with open(file_path, 'w', encoding='utf-8') as f:
            for ip in unique_ips:
                f.write(ip + '\n')
        
        files_created += 1
        print(f"  💾 已保存 {len(unique_ips)} 个IP到 {file_path}")
    
    print(f"\n🎉 抓取完成！")
    print(f"  创建文件数: {files_created}")
    print(f"  总唯一IP数: {total_ips}")
    
    return total_ips, files_created

if __name__ == "__main__":
    try:
        total_ips, files_created = scrape_tonkiang()
        if total_ips == 0:
            print("❌ 警告: 未找到任何IP地址")
            sys.exit(1)
        else:
            sys.exit(0)
    except Exception as e:
        print(f"❌ 脚本执行失败: {e}")
        sys.exit(1)
