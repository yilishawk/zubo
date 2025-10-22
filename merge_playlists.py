import requests
import re
from datetime import datetime
import os

def fetch_url(url):
    """获取URL内容"""
    try:
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8'
        return response.text
    except Exception as e:
        print(f"获取 {url} 失败: {e}")
        return None

def parse_m3u_content(content):
    """解析M3U内容，提取频道和URL"""
    channels = []
    lines = content.split('\n')
    
    for i in range(len(lines)):
        line = lines[i].strip()
        if line.startswith('#EXTINF:'):
            # 解析EXTINF行，提取频道标识
            tvg_id_match = re.search(r'tvg-id="([^"]*)"', line)
            svg_id_match = re.search(r'svg-id="([^"]*)"', line)
            tvg_name_match = re.search(r'tvg-name="([^"]*)"', line)
            svg_name_match = re.search(r'svg-name="([^"]*)"', line)
            channel_name_match = re.search(r',([^,]*)$', line)
            
            # 获取频道名称
            channel_name = channel_name_match.group(1) if channel_name_match else ""
            
            # 优先级：tvg-id > svg-id > tvg-name > svg-name > channel_name
            channel_id = None
            if tvg_id_match:
                channel_id = tvg_id_match.group(1)
            elif svg_id_match:
                channel_id = svg_id_match.group(1)
            elif tvg_name_match:
                channel_id = tvg_name_match.group(1)
            elif svg_name_match:
                channel_id = svg_name_match.group(1)
            else:
                channel_id = channel_name
            
            # 获取下一行的URL
            if i + 1 < len(lines) and not lines[i+1].startswith('#'):
                url = lines[i+1].strip()
                
                if channel_id and url:
                    channels.append({
                        'channel_id': channel_id,
                        'url': url
                    })
    
    return channels

def normalize_channel_name(name):
    """标准化频道名称"""
    if not name:
        return ""
    
    # 转换为小写
    normalized = name.lower()
    
    # 移除中文和空格，只保留字母数字
    normalized = re.sub(r'[^a-z0-9]', '', normalized)
    
    # 映射常见频道名称变体
    channel_mapping = {
        'cctv1zh': 'cctv1',
        'cctv1zhonghe': 'cctv1',
        'cctv1comprehensive': 'cctv1',
        'cctv2cj': 'cctv2', 
        'cctv2caijing': 'cctv2',
        'cctv2finance': 'cctv2',
        'cctv3zy': 'cctv3',
        'cctv3zongyi': 'cctv3',
        'cctv3variety': 'cctv3',
        'cctv4': 'cctv4',
        'cctv5ty': 'cctv5',
        'cctv5tiyu': 'cctv5',
        'cctv5sports': 'cctv5',
        'cctv6dy': 'cctv6',
        'cctv6dianying': 'cctv6',
        'cctv6movie': 'cctv6',
        'cctv7': 'cctv7',
        'cctv8': 'cctv8',
        'cctv9': 'cctv9',
        'cctv10': 'cctv10',
        'cctv11': 'cctv11',
        'cctv12': 'cctv12',
        'cctv13': 'cctv13',
        'cctv14': 'cctv14',
        'cctv15': 'cctv15',
        'cctv16': 'cctv16',
        'cctv17': 'cctv17',
        'cctv5+': 'cctv5plus',
        'cctv5plus': 'cctv5plus',
    }
    
    # 查找匹配的标准化名称
    for key, value in channel_mapping.items():
        if key in normalized:
            return value
    
    # 如果没有匹配，尝试提取cctv+数字的模式
    cctv_match = re.search(r'cctv(\d+)', normalized)
    if cctv_match:
        return f"cctv{cctv_match.group(1)}"
    
    # 尝试其他常见模式
    if 'btv1' in normalized:
        return 'btv1'
    elif 'hnws' in normalized or 'hunan' in normalized:
        return 'hunan'
    elif 'zjws' in normalized or 'zhejiang' in normalized:
        return 'zhejiang'
    elif 'dfws' in normalized or 'dongfang' in normalized:
        return 'dongfang'
    elif 'jsws' in normalized or 'jiangsu' in normalized:
        return 'jiangsu'
    
    return normalized

def merge_all_channels(urls):
    """从所有URL合并频道数据"""
    all_channels = {}
    
    for url in urls:
        print(f"处理URL: {url}")
        content = fetch_url(url)
        
        if content:
            channels = parse_m3u_content(content)
            print(f"从该URL解析到 {len(channels)} 个频道")
            
            for channel in channels:
                norm_id = normalize_channel_name(channel['channel_id'])
                if norm_id:
                    if norm_id not in all_channels:
                        all_channels[norm_id] = []
                    
                    # 避免重复URL
                    if channel['url'] not in all_channels[norm_id]:
                        all_channels[norm_id].append(channel['url'])
    
    return all_channels

def generate_txt_content(all_channels):
    """生成TXT格式内容"""
    content = ""
    
    for channel_id, urls in sorted(all_channels.items()):
        for url in urls:
            content += f"{channel_id},{url}\n"
    
    return content

def main():
    """主函数"""
    # 定义四个链接
    urls = [
        "https://fy.188766.xyz/?ip=&bconly=true&mima=mianfeidehaimaiqian&json=true",
        "https://raw.githubusercontent.com/develop202/migu_video/main/interface.txt",
        # 可以在这里添加更多链接
        # "第三个链接",
        # "第四个链接"
    ]
    
    print("开始获取和融合数据...")
    
    # 合并所有频道的URL
    all_channels = merge_all_channels(urls)
    
    print(f"融合完成！共有 {len(all_channels)} 个唯一频道")
    
    # 统计总URL数量
    total_urls = sum(len(urls) for urls in all_channels.values())
    print(f"总URL数量: {total_urls}")
    
    # 生成TXT内容
    txt_content = generate_txt_content(all_channels)
    
    # 写入文件
    output_file = 'merged_channels.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(txt_content)
    
    print(f"文件已生成: {output_file}")
    
    # 显示前几个频道作为示例
    print("\n前5个频道示例:")
    for i, (channel_id, urls) in enumerate(list(all_channels.items())[:5]):
        print(f"{channel_id}: {len(urls)} 个URL")
        for url in urls[:2]:  # 显示前2个URL
            print(f"  - {url}")

if __name__ == "__main__":
    main()
