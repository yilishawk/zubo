import requests
import re
import os
import time
import sys
import random
from bs4 import BeautifulSoup

def scrape_tonkiang():
    """主抓取函数"""
    output_dir = "tonkiang"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    all_ips_by_province = {}
    total_ips = 0
    
    print("🚀 开始抓取IPTV IP地址...")
    
    # 尝试多种方法
    methods = [
        try_method_selenium_proxy,
        try_method_requests_advanced,
        try_method_simple_requests
    ]
    
    for method in methods:
        print(f"\n🔄 尝试方法: {method.__name__}")
        result = method()
        if result and result[0] > 0:  # 如果找到IP
            total_ips, files_created = result
            break
    else:
        # 所有方法都失败
        print("❌ 所有方法都失败了")
        total_ips, files_created = 0, 0
    
    return save_results(all_ips_by_province, total_ips)

def try_method_selenium_proxy():
    """方法1: 尝试使用代理和高级请求头"""
    print("🔧 使用高级请求头和方法...")
    
    # 轮换User-Agent
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0'
    ]
    
    total_ips = 0
    
    for page in range(1, 5):
        print(f"  📄 抓取第 {page} 页...")
        
        url = f"https://tonkiang.us/iptvmulticast.php?page={page}&iphone16=&code="
        
        headers = {
            'User-Agent': random.choice(user_agents),
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
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
        
        try:
            # 使用会话保持
            session = requests.Session()
            session.headers.update(headers)
            
            # 添加随机延迟
            time.sleep(random.uniform(2, 5))
            
            response = session.get(url, timeout=20)
            
            if response.status_code == 200:
                # 检查是否被阻止
                if any(blocked in response.text for blocked in ['Cloudflare', 'captcha', 'Checking your browser']):
                    print(f"    ❌ 第 {page} 页被Cloudflare阻止")
                    continue
                
                # 保存HTML用于调试
                with open(f"page_{page}_debug.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                
                soup = BeautifulSoup(response.text, 'html.parser')
                ips_found = parse_page(soup, {})
                total_ips += ips_found
                print(f"    ✅ 第 {page} 页找到 {ips_found} 个IP")
            else:
                print(f"    ❌ 第 {page} 页请求失败，状态码: {response.status_code}")
                
        except Exception as e:
            print(f"    ❌ 第 {page} 页异常: {e}")
            continue
    
    return total_ips

def try_method_requests_advanced():
    """方法2: 使用更简单的请求"""
    print("🔧 使用简化请求方法...")
    
    total_ips = 0
    
    for page in range(1, 5):
        print(f"  📄 抓取第 {page} 页...")
        
        url = f"https://tonkiang.us/iptvmulticast.php?page={page}&iphone16=&code="
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                ips_found = parse_page(soup, {})
                total_ips += ips_found
                print(f"    ✅ 第 {page} 页找到 {ips_found} 个IP")
            else:
                print(f"    ❌ 第 {page} 页请求失败")
                
            time.sleep(2)
            
        except Exception as e:
            print(f"    ❌ 第 {page} 页异常: {e}")
            continue
    
    return total_ips

def try_method_simple_requests():
    """方法3: 最基本的请求"""
    print("🔧 使用最基本请求方法...")
    
    total_ips = 0
    
    for page in range(1, 5):
        print(f"  📄 抓取第 {page} 页...")
        
        url = f"https://tonkiang.us/iptvmulticast.php?page={page}&iphone16=&code="
        
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                ips_found = parse_page(soup, {})
                total_ips += ips_found
                print(f"    ✅ 第 {page} 页找到 {ips_found} 个IP")
            else:
                print(f"    ❌ 第 {page} 页请求失败")
                
            time.sleep(1)
            
        except Exception as e:
            print(f"    ❌ 第 {page} 页异常: {e}")
            continue
    
    return total_ips

def parse_page(soup, all_ips_by_province):
    """解析页面内容"""
    ips_found = 0
    
    # 方法1: 查找result div
    result_divs = soup.find_all('div', class_='result')
    
    for i, result in enumerate(result_divs):
        ip = extract_ip_from_result(result)
        if ip:
            province = extract_province_from_result(result)
            
            if province not in all_ips_by_province:
                all_ips_by_province[province] = []
            all_ips_by_province[province].append(ip)
            ips_found += 1
            print(f"      ✅ 找到IP: {ip} - 省份: {province}")
    
    # 方法2: 直接在整个页面中搜索IP
    if ips_found == 0:
        page_text = soup.get_text()
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        all_ips = re.findall(ip_pattern, page_text)
        
        # 过滤掉明显不是服务器IP的地址
        valid_ips = [ip for ip in all_ips if not ip.startswith(('0.', '127.', '169.', '192.168.', '10.', '172.'))]
        
        if valid_ips:
            print(f"      通过正则找到 {len(valid_ips)} 个IP: {valid_ips[:3]}...")
            # 这里可以进一步处理这些IP
    
    return ips_found

def extract_ip_from_result(result):
    """从result div中提取IP地址"""
    ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    
    # 从channel div中提取
    channel_div = result.find('div', class_='channel')
    if channel_div:
        channel_text = channel_div.get_text()
        ip_matches = re.findall(ip_pattern, channel_text)
        if ip_matches:
            return ip_matches[0]
    
    # 从链接中提取
    links = result.find_all('a')
    for link in links:
        href = link.get('href', '')
        link_text = link.get_text()
        
        # 从href中提取
        ip_matches = re.findall(ip_pattern, href)
        if ip_matches:
            return ip_matches[0]
        
        # 从链接文本中提取
        ip_matches = re.findall(ip_pattern, link_text)
        if ip_matches:
            return ip_matches[0]
    
    # 从整个result中提取
    result_text = result.get_text()
    ip_matches = re.findall(ip_pattern, result_text)
    if ip_matches:
        return ip_matches[0]
    
    return None

def extract_province_from_result(result):
    """从result div中提取省份信息"""
    # 查找包含位置信息的div
    location_divs = result.find_all('div', style=re.compile(r'font-size: 11px; color: #aaa;'))
    
    for location_div in location_divs:
        location_text = location_div.get_text()
        
        # 提取省份信息
        province_matches = re.findall(r'([\u4e00-\u9fa5]{2,6}省|[\u4e00-\u9fa5]{2,4}市|[\u4e00-\u9fa5]{2,6}自治区)', location_text)
        if province_matches:
            return province_matches[0]
        
        # 如果没有明确省份，尝试从其他文本中提取
        if '电信' in location_text or '联通' in location_text or '移动' in location_text:
            # 尝试提取城市
            city_matches = re.findall(r'([\u4e00-\u9fa5]{2,4}市)', location_text)
            if city_matches:
                return city_matches[0]
    
    return "其他"

def save_results(all_ips_by_province, total_ips):
    """保存结果到文件"""
    output_dir = "tonkiang"
    files_created = 0
    
    print(f"\n📈 抓取统计:")
    print(f"  总IP数量: {total_ips}")
    print(f"  省份数量: {len(all_ips_by_province)}")
    
    # 如果没有找到IP，创建一个空的结果文件
    if total_ips == 0:
        no_result_file = os.path.join(output_dir, "无结果.txt")
        with open(no_result_file, 'w', encoding='utf-8') as f:
            f.write("本次抓取未找到任何IP地址\n")
        files_created = 1
        print(f"  💾 创建空结果文件: {no_result_file}")
    else:
        # 保存找到的IP
        for province, ips in all_ips_by_province.items():
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

def alternative_scraping():
    """备选方案：如果主网站无法抓取，尝试其他IPTV资源"""
    print("\n🔄 尝试备选IPTV资源...")
    
    # 这里可以添加其他IPTV网站的抓取逻辑
    # 例如：https://iptv-org.github.io/iptv/index.m3u
    # 或者：https://raw.githubusercontent.com/iptv-org/iptv/master/streams/cn.m3u
    
    print("📝 备选资源功能待实现")
    return 0, 0

if __name__ == "__main__":
    try:
        print("=" * 50)
        print("🤖 IPTV IP地址抓取工具")
        print("=" * 50)
        
        total_ips, files_created = scrape_tonkiang()
        
        # 如果主方法失败，尝试备选方案
        if total_ips == 0:
            print("\n🔄 主网站抓取失败，尝试备选方案...")
            total_ips, files_created = alternative_scraping()
        
        # 最终结果
        if total_ips > 0:
            print(f"\n✅ 成功抓取 {total_ips} 个IP地址，保存在 {files_created} 个文件中")
            sys.exit(0)
        else:
            print(f"\n❌ 未能抓取到任何IP地址")
            # 创建标记文件
            with open("SCRAPE_FAILED.txt", "w") as f:
                f.write(f"抓取失败时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 脚本执行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
