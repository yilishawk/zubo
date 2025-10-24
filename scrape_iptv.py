import requests
import re
import os
from bs4 import BeautifulSoup
import time
import sys

def scrape_tonkiang():
    base_url = "https://tonkiang.us/iptvmulticast.php"
    headers = {
        'authority': 'tonkiang.us',
        'method': 'GET',
        'scheme': 'https',
        'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'sec-fetch-site': 'none',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-user': '?1',
        'sec-fetch-dest': 'document',
        'accept-encoding': 'gzip, deflate, br, zstd',
        'accept-language': 'zh-CN,zh;q=0.9',
        'cookie': 'IPTVGO=eb6c67cc; REFERER=Gameover; REFERER2=Game; REFERER1=Over; cf_clearance=6Ya_0Q7hnBoL_Chd.LgkmHyPwIyeO_OkJlREOEqGVDw-1761270271-1.2.1.1-GG1rDyX0BUYytKFPptvP1ukG6Ep4_be48QfvGVVGaRjoVSyOgvoKI1aSTQDYFkZ97r2YTlK5aWxS5hoJgvKldYzMzW.zOxSSNYvte471UDvenZwAAuki2jrjocBA_RpQEoy.hvAeUjy_IYyQ_qGh4.D_W6khDqthvx7EB2GGDCQQ47X6TLxrgTVTi_EbgtUwQ5KkpE7hQNBYaKpTHuic3L9FgX4tFtVTyjEDVQqlCP8',
        'priority': 'u=0, i'
    }
    
    # 创建tonkiang文件夹
    output_dir = "tonkiang"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    all_ips_by_province = {}
    total_ips = 0
    
    print("🚀 开始抓取IPTV IP地址...")
    
    # 抓取4页数据
    for page in range(1, 5):
        print(f"\n📄 正在抓取第 {page} 页...")
        
        params = {
            'page': page,
            'iphone16': '',
            'code': ''
        }
        
        try:
            response = requests.get(base_url, params=params, headers=headers, timeout=10)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找所有的result div
                result_divs = soup.find_all('div', class_='result')
                page_ip_count = 0
                
                for result in result_divs:
                    # 提取IP地址
                    channel_div = result.find('div', class_='channel')
                    if channel_div:
                        a_tag = channel_div.find('a')
                        if a_tag and a_tag.find('b'):
                            ip_text = a_tag.find('b').get_text(strip=True)
                            # 使用正则表达式提取IP地址
                            ip_match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', ip_text)
                            if ip_match:
                                ip = ip_match.group()
                                
                                # 提取省份信息
                                location_info = result.find('div', style='font-size: 11px; color: #aaa;')
                                if location_info:
                                    i_tag = location_info.find('i')
                                    if i_tag:
                                        location_text = i_tag.get_text(strip=True)
                                        # 提取省份
                                        province_match = re.search(r'([\u4e00\u9fa5]{2,6}省|[\uu4e00\u9fa5]{2,4}市|[\u4e00\u9fa5]{2,6}自治区)', location_text)
                                        if province_match:
                                            province = province_match.group(1)
                                        else:
                                            province = "其他"
                                        
                                        # 将IP添加到对应省份的列表中
                                        if province not in all_ips_by_province:
                                            all_ips_by_province[province] = []
                                        all_ips_by_province[province].append(ip)
                                        page_ip_count += 1
                                        total_ips += 1
                                        print(f"  ✅ 找到IP: {ip} - 省份: {province}")
                
                print(f"  📊 第 {page} 页共找到 {page_ip_count} 个IP")
            else:
                print(f"  ❌ 第 {page} 页请求失败，状态码: {response.status_code}")
            
            # 添加延迟避免请求过快
            time.sleep(1)
            
        except requests.RequestException as e:
            print(f"  ❌ 第 {page} 页请求异常: {e}")
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
    
    # 返回统计信息给工作流
    return total_ips, files_created

if __name__ == "__main__":
    try:
        total_ips, files_created = scrape_tonkiang()
        # 设置输出变量供GitHub Actions使用
        print(f"::set-output name=total_ips::{total_ips}")
        print(f"::set-output name=files_created::{files_created}")
    except Exception as e:
        print(f"❌ 脚本执行失败: {e}")
        sys.exit(1)
