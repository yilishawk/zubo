#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 4订阅源TXT合并器 v11.0 - 一行一个 + 同台名多链接
功能：抓取429频道 | 统一台名 | 多链接合并 | 按字母排序
格式：CCTV1 综合,http://链接1
      CCTV1 综合,http://链接2
作者：Grok | 日期：2025-10-22
"""

import requests
import re
import json
from urllib.parse import urlparse
from collections import defaultdict
from datetime import datetime

class TXT_MERGER:
    def __init__(self):
        self.subscriptions = [
            "https://txt.gt.tc/users/HKTV.txt?i=1",
            "http://iptv.4666888.xyz/FYTV.txt",
            "https://fy.188766.xyz/?ip=&bconly=true&mima=mianfeidehaimaiqian&json=true",
            "https://raw.githubusercontent.com/develop202/migu_video/main/interface.txt"
        ]
        
        # 🔥 统一台名映射表
        self.channel_unify = {
            # CCTV - HD/SD统一
            'cctv1': 'CCTV1 综合', 'cctv1hd': 'CCTV1 综合',
            'cctv2': 'CCTV2 财经', 'cctv2hd': 'CCTV2 财经',
            'cctv3': 'CCTV3 综艺', 'cctv3hd': 'CCTV3 综艺',
            'cctv4': 'CCTV4 中文国际', 'cctv4hd': 'CCTV4 中文国际',
            'cctv5': 'CCTV5 体育', 'cctv5hd': 'CCTV5 体育',
            'cctv5plus': 'CCTV5+ 赛事',
            'cctv6': 'CCTV6 电影',
            'cctv7': 'CCTV7 军事',
            'cctv8': 'CCTV8 电视剧', 'cctv8hd': 'CCTV8 电视剧',
            'cctv9': 'CCTV9 纪录',
            'cctv10': 'CCTV10 科教',
            'cctv11': 'CCTV11 戏曲',
            'cctv12': 'CCTV12 社会',
            'cctv13': 'CCTV13 新闻',
            'cctv14': 'CCTV14 少儿',
            'cctv15': 'CCTV15 音乐',
            'cctv16': 'CCTV16 奥运',
            'cctv17': 'CCTV17 农业',
            
            # 卫视
            'dragon': '东方卫视',
            'jgsd': '江苏卫视',
            'zgsd': '浙江卫视',
            'hbs': '湖南卫视',
            'ahws': '安徽卫视',
            'sdws': '山东卫视',
            'gdws': '广东卫视',
            'hnws': '河南卫视',
            'bjws': '北京卫视',
            'tjws': '天津卫视',
            'shws': '上海卫视',
            'cqws': '重庆卫视'
        }
    
    def fetch_content(self, url):
        """抓取内容"""
        try:
            resp = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            resp.raise_for_status()
            return resp.text
        except:
            return ""
    
    def extract_channel_code(self, name_or_url):
        """提取频道代码"""
        text = (name_or_url + " " + name_or_url.lower()).lower()
        for code in self.channel_unify:
            if code in text:
                return code
        return None
    
    def parse_m3u(self, content):
        """解析M3U → (原始名, URL)"""
        streams = []
        lines = content.splitlines()
        current_name = ""
        for line in lines:
            line = line.strip()
            if line.startswith("#EXTINF:"):
                match = re.search(r',(.+)$', line)
                current_name = match.group(1).strip() if match else ""
            elif line.startswith("http") and (".m3u8" in line or ".php" in line):
                streams.append((current_name, line))
                current_name = ""
        return streams
    
    def parse_txt(self, content):
        """解析TXT → (原始名, URL)"""
        streams = []
        lines = content.splitlines()
        for line in lines:
            if "," in line:
                parts = line.split(",", 1)
                if len(parts) >= 2:
                    streams.append((parts[0].strip(), parts[1].strip()))
        return streams
    
    def parse_json(self, content):
        """解析JSON → (原始名, URL)"""
        try:
            data = json.loads(content)
            streams = []
            if isinstance(data, list):
                for item in data:
                    streams.append((item.get('name', ''), item.get('url', '')))
            return streams
        except:
            return []
    
    def unify_and_group(self, all_streams):
        """统一台名 + 分组"""
        channel_groups = defaultdict(list)
        
        for orig_name, url in all_streams:
            # 提取频道代码
            code = self.extract_channel_code(orig_name) or self.extract_channel_code(url)
            
            # 统一台名
            unified_name = self.channel_unify.get(code, orig_name or "未知频道")
            
            # 添加到分组
            if unified_name and url:
                channel_groups[unified_name].append(url)
        
        return channel_groups
    
    def generate_txt(self, channel_groups):
        """生成TXT格式 - 一行一个"""
        lines = []
        # 按台名排序
        for name in sorted(channel_groups.keys()):
            urls = channel_groups[name]
            # 每个链接单独一行
            for url in urls:
                lines.append(f"{name},{url}")
        
        return lines
    
    def run(self):
        """主运行"""
        print("🚀 开始抓取4个订阅源...")
        all_streams = []
        
        # 抓取每个源
        for i, url in enumerate(self.subscriptions, 1):
            print(f"\n📡 [{i}/4] 抓取: {url.split('?')[0]}")
            content = self.fetch_content(url)
            
            if not content:
                print("   ❌ 抓取失败")
                continue
            
            # 解析
            if "?json=true" in url:
                parsed = self.parse_json(content)
            elif url.endswith('.txt'):
                parsed = self.parse_txt(content)
            else:
                parsed = self.parse_m3u(content)
            
            all_streams.extend(parsed)
            print(f"   ✅ 原始数据: {len(parsed)} 行")
        
        # 统一台名 + 分组
        channel_groups = self.unify_and_group(all_streams)
        
        # 生成TXT
        txt_lines = self.generate_txt(channel_groups)
        
        # 保存
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"订阅合并_{date_str}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("\n".join(txt_lines))
        
        print(f"\n🎉 TXT生成完成！")
        print(f"📊 总行数: {len(txt_lines)} 行")
        print(f"📺 唯一台名: {len(channel_groups)} 个")
        print(f"💾 已保存: {filename}")
        
        # 预览前20行
        print("\n📋 TXT预览 (前20行):")
        print("-" * 80)
        for i, line in enumerate(txt_lines[:20], 1):
            print(f"{i:2d}. {line}")
        if len(txt_lines) > 20:
            print("...")
        
        # 台名统计
        print(f"\n📈 台名统计 (Top 10):")
        for i, (name, urls) in enumerate(sorted(channel_groups.items())[:10], 1):
            print(f"{i}. {name:<20} | {len(urls)} 个链接")
        
        return filename, txt_lines

# 🔥 一键运行
if __name__ == "__main__":
    merger = TXT_MERGER()
    filename, lines = merger.run()
    
    print(f"\n🚀 使用方法:")
    print("1. 下载 '{filename}'")
    print("2. VLC → 媒体 → 打开网络串流")
    print("3. 逐行粘贴: 台名,链接")
    print("4. 或导入支持TXT的播放器")
    
    print("\n⏰ 每日定时: crontab -e → 0 8 * * * python3 ylml.py")
    print("\n" + "="*80)
    print(f"✅ {len(lines)} 行TXT已生成！")
