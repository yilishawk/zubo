import requests
import re
import os
from bs4 import BeautifulSoup
import time
import sys

def scrape_tonkiang():
    base_url = "https://tonkiang.us/iptvmulticast.php"
    
    # 使用更简单的headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    # 创建tonkiang文件夹
    output_dir = "tonkiang"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    all_ips_by_province = {}
    total_ips = 0
    
    print("🚀 开始抓取IPTV IP地址...")
    print(f"目标URL: {base_url}")
    
    # 抓取4页数据
    for page in range(1, 5):
        print(f"\n📄 正在抓取第 {page} 页...")
        
        url = f"https://tonkiang.us/iptvmulticast.php?page={page}&iphone16=&code="
        print(f"请求URL: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            print(f"响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                # 保存原始HTML用于调试
                with open(f"debug_page_{page}.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                print(f"✅ 第 {page} 页HTML已保存到 debug_page_{page}.html")
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 调试：查找所有包含IP的可能元素
                print("🔍 搜索包含IP地址的元素...")
                
                # 方法1：查找所有包含IP地址的文本
                ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
                all_text_ips = re.findall(ip_pattern, response.text)
                print(f"文本中找到的IP数量: {len(all_text_ips)}")
                if all_text_ips:
                    print(f"示例IP: {all_text_ips[:5]}")
                
                # 方法2：查找特定的HTML结构
                result_divs = soup.find_all('div', class_='result')
                print(f"找到的result div数量: {len(result_divs)}")
                
                page_ip_count = 0
                
                for i, result in enumerate(result_divs):
                    print(f"  分析第 {i+1} 个result div...")
                    
                    # 提取IP地址 - 多种方法尝试
                    ip = None
                    province = "其他"
                    
                    # 方法1：从channel div中提取
                    channel_div = result.find('div', class_='channel')
                    if channel_div:
                        channel_text = channel_div.get_text()
                        ip_matches = re.findall(ip_pattern, channel_text)
                        if ip_matches:
                            ip = ip_matches[0]
                            print(f"    从channel找到IP: {ip}")
                    
                    # 方法2：从所有链接中提取
                    if not ip:
                        links = result.find_all('a')
                        for link in links:
                            href = link.get('href', '')
                            link_text = link.get_text()
                            # 从href中提取IP
                            ip_matches = re.findall(ip_pattern, href)
                            if ip_matches:
                                ip = ip_matches[0]
                                print(f"    从链接href找到IP: {ip}")
                                break
                            # 从链接文本中提取IP
                            ip_matches = re.findall(ip_pattern, link_text)
                            if ip_matches:
                                ip = ip_matches[0]
                                print(f"    从链接文本找到IP: {ip}")
                                break
                    
                    # 方法3：从整个result div中提取
                    if not ip:
                        result_text = result.get_text()
                        ip_matches = re.findall(ip_pattern, result_text)
                        if ip_matches:
                            ip = ip_matches[0]
                            print(f"    从result文本找到IP: {ip}")
                    
                    if ip:
                        # 提取省份信息
                        location_divs = result.find_all('div', style=re.compile(r'font-size: 11px; color: #aaa;'))
                        for location_div in location_divs:
                            location_text = location_div.get_text()
                            print(f"    位置文本: {location_text}")
                            
                            # 提取省份信息
                            province_matches = re.findall(r'([\u4e00-\u9fa5]{2,6}省|[\u4e00-\u9fa5]{2,4}市|[\u4e00-\u9fa5]{2,6}自治区)', location_text)
                            if province_matches:
                                province = province_matches[0]
                                print(f"    找到省份: {province}")
                                break
                        
                        # 将IP添加到对应省份的列表中
                        if province not in all_ips_by_province:
                            all_ips_by_province[province] = []
                        all_ips_by_province[province].append(ip)
                        page_ip_count += 1
                        total_ips += 1
                        print(f"    ✅ 成功记录IP: {ip} - 省份: {province}")
                    else:
                        print(f"    ❌ 第 {i+1} 个result div中未找到IP")
                
                print(f"  📊 第 {page} 页共找到 {page_ip_count} 个IP")
            else:
                print(f"  ❌ 第 {page} 页请求失败，状态码: {response.status_code}")
                print(f"  响应内容前500字符: {response.text[:500]}")
            
            # 添加延迟避免请求过快
            time.sleep(2)
            
        except requests.RequestException as e:
            print(f"  ❌ 第 {page} 页请求异常: {e}")
            continue
        except Exception as e:
            print(f"  ❌ 第 {page} 页处理异常: {e}")
            continue
    
    print(f"\n📈 抓取统计:")
    print(f"  总IP数量: {total_ips}")
    print(f"  省份数量: {len(all_ips_by_province)}")
    
    # 将IP地址写入对应的省份文件
    files_created = 0
    for province, ips in all_ips_by_province.items():
        # 清理文件名中的非法字符
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
    
    # 如果没有找到任何IP，保存一个标记文件
    if total_ips == 0:
        with open("no_ips_found.txt", "w") as f:
            f.write("本次抓取未找到任何IP地址\n")
        print("❌ 警告: 未找到任何IP地址")
    
    return total_ips, files_created

if __name__ == "__main__":
    try:
        total_ips, files_created = scrape_tonkiang()
        # 退出码用于GitHub Actions判断
        if total_ips == 0:
            sys.exit(1)  # 没有找到IP，返回错误码
        else:
            sys.exit(0)  # 成功找到IP
    except Exception as e:
        print(f"❌ 脚本执行失败: {e}")
        sys.exit(1)
