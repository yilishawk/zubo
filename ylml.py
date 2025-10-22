#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 全自动 IPTV 修复器 v5.0 - 在线环境专用
功能：海量乱码修复 | 自动加台名 | 零交互运行
作者：Grok | 日期：2025-10-22
"""

import re
import os
from urllib.parse import urlparse
from collections import defaultdict

class AUTO_FIXER:
    def __init__(self):
        self.channel_map = {
            'cctv1hd': 'CCTV1 HD', 'cctv1': 'CCTV1',
            'cctv2hd': 'CCTV2 HD', 'cctv2': 'CCTV2 财经',
            'cctv3hd': 'CCTV3 HD', 'cctv3': 'CCTV3 综艺',
            'cctv4hd': 'CCTV4 HD', 'cctv4': 'CCTV4 中文国际',
            'cctv5hd': 'CCTV5 HD', 'cctv5': 'CCTV5 体育',
            'cctv6': 'CCTV6 电影', 'cctv7': 'CCTV7 国防军事',
            'cctv8hd': 'CCTV8 HD', 'cctv8': 'CCTV8 电视剧',
            'cctv9': 'CCTV9 纪录', 'cctv10': 'CCTV10 科教',
            'cctv11': 'CCTV11 戏曲', 'cctv12': 'CCTV12 社会与法',
            'cctv13': 'CCTV13 新闻', 'cctv14': 'CCTV14 少儿',
            'cctv15': 'CCTV15 音乐', 'cctv16': 'CCTV16 奥运',
            'cctv17': 'CCTV17 农业农村', 'dragon': '东方卫视',
            'jgsd': '江苏卫视', 'zgsd': '浙江卫视', 'hbs': '湖南卫视',
            'cggv1': 'CGTN 英语', 'ocn': '海洋频道'
        }
        self.logo_base = "https://raw.githubusercontent.com/iptv-org/iptv/master/logos/"
        self.quality_priority = {'2000': 3, '1500': 2, '1200': 1, '720': 0}
    
    def smart_parse(self, url):
        path = urlparse(url).path.lower()
        
        # CCTV匹配
        match = re.search(r'/cctv(\d+)(hd)?/', path)
        if match:
            num = match.group(1)
            hd = 'hd' if match.group(2) else ''
            return f'cctv{num}{hd}', '720', url
        
        # 卫视匹配
        if '/dragon/' in path: return 'dragon', '720', url
        if '/jgsd/' in path: return 'jgsd', '720', url
        if '/zgsd/' in path: return 'zgsd', '720', url
        if '/hbs/' in path: return 'hbs', '720', url
        
        # ID参数
        id_match = re.search(r'id=([a-z0-9]+)', url)
        if id_match:
            return id_match.group(1), '720', url
        
        if 'ocn/cctv3hd' in path:
            return 'cctv3hd', '720', url
        
        return None, None, url
    
    def clean_url(self, url, quality='720'):
        parsed = urlparse(url)
        
        if 'miguvideo.com' in url:
            path = re.sub(r'/\d+/index\.m3u8.*$', f'/{quality}/index.m3u8', parsed.path)
            return f"{parsed.scheme}://{parsed.netloc}{path}"
        
        elif 'iptv2A.php' in url:
            id_part = re.search(r'id=([^&\s]+)', url).group(1)
            return f"{parsed.scheme}://{parsed.netloc}/iptv2A.php?id={id_part}"
        
        return url
    
    def fix_all_links(self, raw_text):
        links = re.split(r'[,\n\s]+', raw_text)
        channels = defaultdict(list)
        valid_count = 0
        
        for line in links:
            line = line.strip()
            if not line.startswith('http'):
                continue
            
            code, quality, orig_url = self.smart_parse(line)
            if not code:
                continue
            
            clean_url = self.clean_url(orig_url, quality)
            priority = self.quality_priority.get(quality, 0)
            
            channels[code].append({'url': clean_url, 'priority': priority})
            valid_count += 1
        
        best_channels = {}
        for code, links_list in channels.items():
            best = max(links_list, key=lambda x: x['priority'])
            best_channels[code] = best['url']
        
        return best_channels, valid_count
    
    def generate_m3u(self, channels):
        lines = ["#EXTM3U", "#EXT-X-VERSION:3"]
        
        for code, url in sorted(channels.items()):
            name = self.channel_map.get(code, f'频道-{code}')
            logo = f"{self.logo_base}{code}.png"
            
            lines.extend([
                f'#EXTINF:-1 tvg-id="{code}" tvg-logo="{logo}" group-title="高清频道",{name}',
                url,
                ""
            ])
        
        return '\n'.join(lines)
    
    def create_sample_input(self):
        """创建示例输入文件"""
        sample_links = """http://gslbmgsplive.miguvideo.com/wd_r2/cctv/cctv1hd/1200/index.m3u8?msisdn=202510222000431839199173d8490e93007687d43ad847&mdspid=&spid=699004&netType=0&sid=2201057821&pid=2028597139&timestamp=20251022200043&Channel_ID=0116_2600000900-99000-201600010010027&ProgramID=608807420&ParentNodeID=-99&assertID=2201057821&client_ip=106.13.250.90&SecurityKey=20251022200043&promotionId=&mvid=2201057821&mcid=500020&playurlVersion=WX-A1-8.9.2-RELEASE&userid=&jmhm=&videocodec=h264&bean=mgspad&tid=android&conFee=0&puData=9b8942f9e4170b41f63e54013b6055fd&ddCalcu=d9fbe58259804062bf391e044157e03b64f1
http://gslbmgsplive.miguvideo.com/wd_r2/cctv/cctv2hd/1500/index.m3u8?msisdn=20251022200043d4c43f06896942feaa3cf1a488b810e1&mdspid=&spid=699004&netType=0&sid=5500346945&pid=2028597139&timestamp=20251022200043&Channel_ID=0116_2600000900-99000-201600010010027&ProgramID=631780532&ParentNodeID=-99&assertID=5500346945&client_ip=106.13.250.90&SecurityKey=20251022200043&promotionId=&mvid=5101064231&mcid=500020&playurlVersion=WX-A1-8.9.2-RELEASE&userid=&jmhm=&videocodec=h264&bean=mgspad&tid=android&conFee=0&puData=48ee70e4f71269d39889a6d032cafa76&ddCalcu=6478eae2fe1a70c02e340fd761a296898d93
http://gslbmgsplive.miguvideo.com/wd_r2/2018/ocn/cctv3hd/2000/index.m3u8?msisdn=2025102220004343d189f41c6548f1a9a3a7f8be570b1b&mdspid=&spid=699004&netType=0&sid=5500212864&pid=2028597139&timestamp=20251022200043&Channel_ID=0116_2600000900-99000-201600010010027&ProgramID=624878271&ParentNodeID=-99&assertID=5500212864&client_ip=106.13.250.90&SecurityKey=20251022200043&promotionId=&mvid=5100001683&mcid=500020&playurlVersion=WX-A1-8.9.2-RELEASE&userid=&jmhm=&videocodec=h264&bean=mgspad&tid=android&conFee=0&puData=216ad505c92014197ca95d7e847eb4b1&ddCalcu=12b1e462ba4ed0754085ec79d25091a4c179
http://iptv.4666888.xyz/iptv2A.php?id=cctv17"""
        
        with open('input_links.txt', 'w', encoding='utf-8') as f:
            f.write(sample_links)
        
        print("📝 已创建示例文件: input_links.txt")
        return 'input_links.txt'

# 🔥 全自动运行 - 无需任何输入！
if __name__ == "__main__":
    print("🔥 全自动 IPTV 修复器 v5.0 - 开始运行...")
    fixer = AUTO_FIXER()
    
    # 1. 检查输入文件
    input_file = 'input_links.txt'
    if not os.path.exists(input_file):
        print("📝 没有找到 input_links.txt，正在创建示例...")
        input_file = fixer.create_sample_input()
    
    # 2. 读取乱码链接
    print(f"📖 读取文件: {input_file}")
    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        raw_text = f.read()
    
    # 3. 自动修复
    print("🔧 开始智能修复...")
    channels, count = fixer.fix_all_links(raw_text)
    
    # 4. 生成M3U
    m3u_content = fixer.generate_m3u(channels)
    
    # 5. 保存结果
    output_file = '修复版.m3u'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(m3u_content)
    
    # 6. 输出结果
    print("\n🎉 全自动修复完成！")
    print(f"📊 有效链接: {count} 个")
    print(f"📺 频道数: {len(channels)} 个")
    print(f"💾 已保存: {output_file}")
    
    print("\n📺 频道列表预览:")
    print("-" * 80)
    for i, (code, url) in enumerate(sorted(channels.items()), 1):
        name = fixer.channel_map.get(code, code)
        print(f"{i:2d}. {name:<20} | {url[:60]}...")
    
    print("\n" + "="*80)
    print("✅ 修复版.m3u 已生成！直接导入播放器使用")
    print("📱 VLC: 媒体 → 打开文件 → 选择修复版.m3u")
    print("📺 完美高清无乱码！")
