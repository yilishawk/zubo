import asyncio
import aiohttp
import subprocess
import os
import re
import time
import threading
import datetime
import json
import psutil
import gc
import resource
import weakref
import glob
import logging
import pytz
from datetime import timedelta
from urllib.parse import urljoin
from flask import Flask, send_file, make_response, Response, request
from collections import OrderedDict

SERVICE_START_TIME = time.time()
RLIMIT_SUPPORTED = True
STOP_EVENT = threading.Event()

IS_FIRST_RUN = True
FIRST_RUN_LIMIT = 20000
MAX_SOURCES_TO_WRITE = 8
MAX_SOURCES_PER_CHANNEL = 30
PORT = int(os.getenv("PORT", 5000))
UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", 21600))
CLEAN_INTERVAL = 43200
OUTPUT_FILE = "/app/output/list.txt"
PLACEHOLDER_FILE = "/app/output/list_placeholder.txt"

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "config")
CHANNEL_CONFIG_FILE = os.path.join(CONFIG_DIR, "channels.json")

CPU = psutil.cpu_count(logical=True) or 2
AUTO_FFPROBE = max(4, min(8, CPU // 2))
FFPROBE_CONCURRENCY = int(os.getenv("FFPROBE_CONCURRENCY", AUTO_FFPROBE))
JSON_CONCURRENCY = int(os.getenv("JSON_CONCURRENCY", FFPROBE_CONCURRENCY * 4))
CONCURRENCY = int(os.getenv("CONCURRENCY", JSON_CONCURRENCY + 100))
FFPROBE_TIMEOUT = int(os.getenv("FFPROBE_TIMEOUT", 6))

def get_elapsed_time():
    elapsed = time.time() - SERVICE_START_TIME
    h = int(elapsed // 3600)
    m = int((elapsed % 3600) // 60)
    s = int(elapsed % 60)
    return f"{h:02d}-{m:02d}-{s:02d}" if h else f"{m:02d}-{s:02d}"

def init_config_dir():
    """初始化配置目录"""
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        print(f"📁 配置目录初始化完成：{CONFIG_DIR}（{get_elapsed_time()}）")

def load_channel_config():
    """加载分类+映射配置（无则初始化默认值）"""
    init_config_dir()
    default_config = OrderedDict([
        ("categories", OrderedDict([
            ("央视频道", ["CCTV1", "CCTV2", "CCTV3", "CCTV4", "CCTV4欧洲", "CCTV4美洲", "CCTV5", "CCTV5+", "CCTV6", "CCTV7", "CCTV8", "CCTV9", 
                      "CCTV10", "CCTV11", "CCTV12", "CCTV13", "CCTV14", "CCTV15", "CCTV16", "CCTV17", "兵器科技", "风云音乐", "风云足球", "风云剧场", 
                      "怀旧剧场", "第一剧场", "女性时尚", "世界地理", "央视台球", "高尔夫网球", "央视文化精品", "卫生健康", "电视指南", "老故事", "中学生", 
                      "发现之旅", "书法频道", "国学频道", "环球奇观"]),
            ("卫视频道", ["湖南卫视", "浙江卫视", "江苏卫视", "东方卫视", "深圳卫视", "北京卫视", "广东卫视", "广西卫视", "东南卫视", "海南卫视", "河北卫视", 
                      "河南卫视", "湖北卫视", "江西卫视", "四川卫视", "重庆卫视", "贵州卫视", "云南卫视", "天津卫视", "安徽卫视", "山东卫视", "辽宁卫视", 
                      "黑龙江卫视", "吉林卫视", "内蒙古卫视", "宁夏卫视", "山西卫视", "陕西卫视", "甘肃卫视", "青海卫视", "新疆卫视", "西藏卫视", "三沙卫视", 
                      "兵团卫视", "延边卫视", "安多卫视", "康巴卫视", "农林卫视", "山东教育卫视", "中国教育1台", "中国教育2台", "中国教育3台", "中国教育4台", 
                      "早期教育"]),
            ("数字频道", ["CHC动作电影", "CHC家庭影院", "CHC影迷电影", "重温经典", "星空卫视", "CHANNELV", "凤凰卫视中文台", "凤凰卫视资讯台", "凤凰卫视香港台", 
                      "凤凰卫视电影台", "求索纪录", "求索科学", "求索生活", "求索动物", "纪实人文", "金鹰纪实", "纪实科教", "魅力足球", "五星体育", "劲爆体育", 
                      "快乐垂钓", "茶频道", "先锋乒羽", "天元围棋", "汽摩", "梨园频道", "文物宝库", "武术世界", "乐游", "生活时尚", "都市剧场", "欢笑剧场", 
                      "游戏风云", "金色学堂", "动漫秀场", "新动漫", "卡酷少儿", "金鹰卡通", "优漫卡通", "哈哈炫动", "嘉佳卡通", "中国交通", "中国天气"])
        ])),
        ("mapping", OrderedDict([
            ("CCTV1", ["CCTV-1", "CCTV1-综合", "CCTV-1 综合", "CCTV-1综合", "CCTV1HD", "CCTV-1高清", "CCTV-1HD", "cctv-1HD", "CCTV1综合高清", "cctv1"]),
            ("CCTV2", ["CCTV-2", "CCTV2-财经", "CCTV-2 财经", "CCTV-2财经", "CCTV2HD", "CCTV-2高清", "CCTV-2HD", "cctv-2HD", "CCTV2财经高清", "cctv2"]),
            ("CCTV3", ["CCTV-3", "CCTV3-综艺", "CCTV-3 综艺", "CCTV-3综艺", "CCTV3HD", "CCTV-3高清", "CCTV-3HD", "cctv-3HD", "CCTV3综艺高清", "cctv3"]),
            ("CCTV4", ["CCTV-4", "CCTV4-国际", "CCTV-4 中文国际", "CCTV-4中文国际", "CCTV4HD", "cctv4HD", "CCTV-4HD", "cctv-4HD", "CCTV4国际高清", "cctv4"]),
            ("CCTV4欧洲", ["CCTV4欧洲", "CCTV-4欧洲", "CCTV4-中文国际欧洲版", "CCTV-4 欧洲"]),
            ("CCTV4美洲", ["CCTV4美洲", "CCTV-4美洲", "CCTV4-中文国际美洲版", "CCTV-4 美洲"]),
            ("CCTV5", ["CCTV-5", "CCTV5-体育", "CCTV-5 体育", "CCTV-5体育", "CCTV5HD", "CCTV-5高清", "CCTV-5HD", "cctv-5HD", "CCTV5体育高清", "cctv5"]),
            ("CCTV5+", ["CCTV-5+", "CCTV-5+ HD", "CCTV-5+ 体育赛事", "CCTV5+体育赛事", "CCTV5+HD", "CCTV-5+高清", "CCTV-5+HD", "cctv-5+HD", "CCTV5plas", "CCTV5+体育赛视高清", "cctv5+"]),
            ("CCTV6", ["CCTV-6", "CCTV6-电影", "CCTV-6 电影", "CCTV-6电影", "CCTV6HD", "CCTV-6高清", "CCTV-6HD", "cctv-6HD", "CCTV6电影高清", "cctv6"]),
            ("CCTV7", ["CCTV-7", "CCTV7-军农", "CCTV-7 国防军事", "CCTV-7国防军事", "CCTV7HD", "CCTV-7高清", "CCTV-7HD", "cctv-7HD", "CCTV7军事高清", "cctv7"]),
            ("CCTV8", ["CCTV-8", "CCTV8-电视剧", "CCTV-8 电视剧", "CCTV-8电视剧", "CCTV8HD", "CCTV-8高清", "CCTV-8HD", "cctv-8HD", "CCTV8电视剧高清", "cctv8"]),
            ("CCTV9", ["CCTV-9", "CCTV9-纪录", "CCTV-9 纪录", "CCTV-9纪录", "CCTV9HD", "CCTV-9高清", "CCTV-9HD", "cctv-9HD", "CCTV9纪录高清", "cctv9"]),
            ("CCTV10", ["CCTV-10", "CCTV10-科教", "CCTV-10 科教", "CCTV-10科教", "CCTV10HD", "CCTV-10高清", "CCTV-10HD", "cctv-10HD", "CCTV10科教高清", "cctv10"]),
            ("CCTV11", ["CCTV-11", "CCTV11-戏曲", "CCTV-11 戏曲", "CCTV-11戏曲", "CCTV11HD", "CCTV-11高清", "CCTV-11HD", "cctv-11HD", "CCTV11戏曲高清", "cctv11"]),
            ("CCTV12", ["CCTV-12", "CCTV12-社会与法", "CCTV-12 社会与法", "CCTV-12社会与法", "CCTV12HD", "CCTV-12高清", "CCTV-12HD", "cctv-12HD", "CCTV12社会与法高清", "cctv12"]),
            ("CCTV13", ["CCTV-13", "CCTV13-新闻", "CCTV-13 新闻", "CCTV-13新闻", "CCTV13HD", "CCTV-13高清", "CCTV-13HD", "cctv-13HD", "CCTV13新闻高清", "cctv13"]),
            ("CCTV14", ["CCTV-14", "CCTV14-少儿", "CCTV-14 少儿", "CCTV-14少儿", "CCTV14HD", "CCTV-14高清", "CCTV-14HD", "cctv-14HD", "CCTV14少儿高清", "cctv14"]),
            ("CCTV15", ["CCTV-15", "CCTV15-音乐", "CCTV-15 音乐", "CCTV-15音乐", "CCTV15HD", "CCTV-15高清", "CCTV-15HD", "cctv-15HD", "CCTV15音乐高清", "cctv15"]),
            ("CCTV16", ["CCTV-16", "CCTV16-奥林匹克", "CCTV-16 奥林匹克", "CCTV16HD", "CCTV-16高清", "cctv16"]),
            ("CCTV17", ["CCTV-17", "CCTV17-农业农村", "CCTV-17 农业农村", "CCTV17HD", "CCTV-17高清", "cctv17"]),
            ("兵器科技", ["CCTV兵器高清", "CCTV兵器科技", "兵器科技频道"]),
            ("风云音乐", ["CCTV风云音乐高清", "CCTV风云音乐", "风云音乐频道"]),
            ("风云足球", ["CCTV风云足球高清", "CCTV风云足球", "风云足球频道"]),
            ("风云剧场", ["CCTV风云剧场高清", "CCTV风云剧场", "风云剧场频道"]),
            ("怀旧剧场", ["CCTV怀旧剧场高清", "CCTV怀旧剧场", "怀旧剧场频道"]),
            ("第一剧场", ["CCTV第一剧场高清", "CCTV第一剧场", "第一剧场频道"]),
            ("女性时尚", ["CCTV女性时尚高清", "CCTV女性时尚", "女性时尚频道"]),
            ("世界地理", ["CCTV世界地理高清", "CCTV世界地理", "世界地理频道"]),
            ("央视台球", ["CCTV央视台球高清", "CCTV台球频道"]),
            ("高尔夫网球", ["CCTV高尔夫网球高清", "CCTV高尔夫·网球", "高尔夫·网球频道"]),
            ("央视文化精品", ["央视文化精品", "CCTV文化精品频道", "央视文化", "文化精品"]),
            ("卫生健康", ["卫生健康", "CCTV卫生健康频道"]),
            ("电视指南", ["电视指南", "CCTV电视指南频道"]),
            ("老故事", ["老故事", "CCTV老故事频道"]),
            ("中学生", ["中学生", "CCTV中学生频道"]),
            ("发现之旅", ["发现之旅", "CCTV发现之旅频道"]),
            ("书法频道", ["书法频道", "CCTV书法频道"]),
            ("国学频道", ["国学频道", "CCTV国学频道"]),
            ("环球奇观", ["环球奇观", "CCTV环球奇观频道"]),
            ("湖南卫视", ["湖南卫视", "湖南卫视高清", "湖南卫视HD"]),
            ("浙江卫视", ["浙江卫视", "浙江卫视HD", "浙江卫视高清"]),
            ("江苏卫视", ["江苏卫视", "江苏卫视hd", "江苏卫视高清"]),
            ("东方卫视", ["东方卫视", "东方卫视hd", "上海卫视", "东方卫视高清"]),
            ("深圳卫视", ["深圳卫视", "深圳卫视hd", "深圳卫视高清"]),
            ("北京卫视", ["北京卫视", "北京卫视hd", "北京卫视高清"]),
            ("广东卫视", ["广东卫视", "广东卫视hd", "广东卫视高清"]),
            ("广西卫视", ["广西卫视", "广西卫视hd", "广西卫视高清"]),
            ("东南卫视", ["东南卫视", "福建东南卫视", "福建东南", "东南卫视高清"]),
            ("海南卫视", ["海南卫视", "海南卫视hd", "旅游卫视", "海南卫视高清"]),
            ("河北卫视", ["河北卫视", "河北卫视hd", "河北卫视高清"]),
            ("河南卫视", ["河南卫视", "河南卫视hd", "河南卫视高清"]),
            ("湖北卫视", ["湖北卫视", "湖北卫视hd", "湖北卫视高清"]),
            ("江西卫视", ["江西卫视", "江西卫视hd", "江西卫视高清"]),
            ("四川卫视", ["四川卫视", "四川卫视hd", "四川卫视高清"]),
            ("重庆卫视", ["重庆卫视", "重庆卫视hd", "重庆卫视高清"]),
            ("贵州卫视", ["贵州卫视", "贵州卫视hd", "贵州卫视高清"]),
            ("云南卫视", ["云南卫视", "云南卫视hd", "云南卫视高清"]),
            ("天津卫视", ["天津卫视", "天津卫视hd", "天津卫视高清"]),
            ("安徽卫视", ["安徽卫视", "安徽卫视hd", "安徽卫视高清"]),
            ("山东卫视", ["山东卫视", "山东卫视hd", "山东卫视高清"]),
            ("辽宁卫视", ["辽宁卫视", "辽宁卫视hd", "辽宁卫视高清"]),
            ("黑龙江卫视", ["黑龙江卫视", "黑龙江卫视hd", "黑龙江卫视高清"]),
            ("吉林卫视", ["吉林卫视", "吉林卫视hd", "吉林卫视高清"]),
            ("内蒙古卫视", ["内蒙古卫视", "内蒙古卫视hd", "内蒙古卫视高清"]),
            ("宁夏卫视", ["宁夏卫视", "宁夏卫视hd", "宁夏卫视sd"]),
            ("山西卫视", ["山西卫视", "山西卫视hd", "山西卫视sd"]),
            ("陕西卫视", ["陕西卫视", "陕西卫视hd", "陕西卫视高清"]),
            ("甘肃卫视", ["甘肃卫视高清", "甘肃卫视hd", "甘肃卫视sd"]),
            ("青海卫视", ["青海卫视高清", "青海卫视hd", "青海卫视sd"]),
            ("新疆卫视", ["新疆卫视", "新疆卫视sd"]),
            ("西藏卫视", ["西藏卫视", "西藏卫视sd"]),
            ("三沙卫视", ["三沙卫视高清", "三沙卫视hd"]),
            ("兵团卫视", ["兵团卫视", "新疆兵团卫视"]),
            ("延边卫视", ["延边卫视", "延边电视台"]),
            ("安多卫视", ["安多卫视", "安多电视台"]),
            ("康巴卫视", ["康巴卫视", "康巴电视台"]),
            ("农林卫视", ["农林卫视", "陕西农林卫视"]),
            ("山东教育卫视", ["山东教育", "山东教育卫视sd"]),
            ("中国教育1台", ["中国教育1台", "CETV1", "教育1台"]),
            ("中国教育2台", ["中国教育2台", "CETV2", "教育2台"]),
            ("中国教育3台", ["中国教育3台", "CETV3", "教育3台"]),
            ("中国教育4台", ["中国教育4台", "CETV4", "教育4台"]),
            ("早期教育", ["早期教育", "CETV早期教育频道"]),
            ("CHC动作电影", ["CHC动作电影", "CHC动作", "CHC动作电影高清"]),
            ("CHC家庭影院", ["CHC家庭影院", "CHC家庭", "CHC家庭电影高清"]),
            ("CHC影迷电影", ["CHC高清电影", "CHC-影迷电影", "影迷电影", "chc高清电影"]),
            ("重温经典", ["重温经典", "重温经典频道"]),
            ("星空卫视", ["星空卫视", "Star TV", "星空台"]),
            ("CHANNELV", ["Channel [V]", "Channel[V]"]),
            ("凤凰卫视中文台", ["凤凰中文", "凤凰中文台", "凤凰卫视中文", "凤凰卫视"]),
            ("凤凰卫视资讯台", ["凤凰资讯", "凤凰资讯台", "凤凰咨询", "凤凰咨询台", "凤凰卫视咨询台", "凤凰卫视资讯", "凤凰卫视咨询"]),
            ("凤凰卫视香港台", ["凤凰香港台", "凤凰卫视香港", "凤凰香港"]),
            ("凤凰卫视电影台", ["凤凰卫视电影台", "凤凰电影台"]),
            ("求索纪录", ["求索纪录", "求索纪录频道"]),
            ("求索科学", ["求索科学", "求索科学频道"]),
            ("求索生活", ["求索生活", "求索生活频道"]),
            ("求索动物", ["求索动物", "求索动物频道"]),
            ("纪实人文", ["纪实人文", "纪实人文频道"]),
            ("金鹰纪实", ["金鹰纪实", "金鹰纪实频道"]),
            ("纪实科教", ["纪实科教", "纪实科教频道"]),
            ("魅力足球", ["魅力足球", "魅力足球频道"]),
            ("五星体育", ["五星体育", "上海五星体育"]),
            ("劲爆体育", ["劲爆体育", "劲爆体育频道"]),
            ("快乐垂钓", ["快乐垂钓", "快乐垂钓频道"]),
            ("茶频道", ["茶频道", "茶文化频道"]),
            ("先锋乒羽", ["先锋乒羽", "先锋乒羽频道"]),
            ("天元围棋", ["天元围棋", "天元围棋频道"]),
            ("汽摩", ["汽摩频道", "汽车摩托车频道"]),
            ("梨园频道", ["梨园频道", "戏曲梨园频道"]),
            ("文物宝库", ["文物宝库", "文物宝库频道"]),
            ("武术世界", ["武术世界", "武术世界频道"]),
            ("乐游", ["乐游频道", "旅游频道"]),
            ("生活时尚", ["生活时尚", "生活时尚频道"]),
            ("都市剧场", ["都市剧场", "都市剧场频道"]),
            ("欢笑剧场", ["欢笑剧场", "欢笑剧场频道"]),
            ("游戏风云", ["游戏风云", "游戏风云频道"]),
            ("金色学堂", ["金色学堂", "金色学堂频道"]),
            ("动漫秀场", ["动漫秀场", "动漫秀场频道"]),
            ("新动漫", ["新动漫", "新动漫频道"]),
            ("卡酷少儿", ["卡酷少儿", "北京卡酷少儿"]),
            ("金鹰卡通", ["金鹰卡通", "湖南金鹰卡通"]),
            ("优漫卡通", ["优漫卡通", "江苏优漫卡通"]),
            ("哈哈炫动", ["哈哈炫动", "上海哈哈炫动"]),
            ("嘉佳卡通", ["嘉佳卡通", "广东嘉佳卡通"]),
            ("中国交通", ["中国交通", "中国交通频道"]),
            ("中国天气", ["中国天气", "中国天气频道"])
        ]))
    ])
    try:
        if not os.path.exists(CHANNEL_CONFIG_FILE):
            with open(CHANNEL_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            print(f"📝 默认配置文件生成：{CHANNEL_CONFIG_FILE}（{get_elapsed_time()}）")
            return default_config
        with open(CHANNEL_CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f, object_pairs_hook=OrderedDict)
        if "mapping" not in config:
            config["mapping"] = default_config["mapping"]
            with open(CHANNEL_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        return config
    except Exception as e:
        print(f"⚠️ 加载配置失败，使用默认配置：{e}（{get_elapsed_time()}）")
        return default_config

def save_channel_config(new_config):
    """保存分类+映射配置"""
    init_config_dir()
    try:
        if not isinstance(new_config.get("categories"), dict) or not isinstance(new_config.get("mapping"), dict):
            return False, "配置格式错误：categories和mapping必须是字典"
        save_config = OrderedDict()
        save_config["categories"] = OrderedDict(new_config["categories"])
        save_config["mapping"] = OrderedDict(new_config["mapping"])
        with open(CHANNEL_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(save_config, f, ensure_ascii=False, indent=2)
        return True, "分类+映射配置保存成功"
    except Exception as e:
        return False, f"保存失败：{str(e)}"

def force_gc():
    gc.collect()
    gc.collect()
    mem = psutil.virtual_memory()
    print(f"📊 内存回收后：已用 {mem.percent}% | 可用 {mem.available/1024/1024:.0f}MB（{get_elapsed_time()}）")

async def safe_session_close(session):
    try:
        await session.close()
        await asyncio.sleep(0.3)
    except:
        pass
    del session
    force_gc()

async def probe_has_video(url):
    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "error",
            "-show_entries", "stream=codec_type,width,height",
            "-of", "json", "-i", url,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=FFPROBE_TIMEOUT)
        if proc.returncode is None:
            proc.kill()
        await proc.wait()
        if proc.returncode != 0:
            return False
        data = json.loads(out.decode(errors="ignore"))
        for s in data.get("streams", []):
            if s.get("codec_type") == "video" and s.get("width", 0) > 0:
                return True
        return False
    except:
        return False
    finally:
        if proc and proc.returncode is None:
            try:
                proc.kill()
                await proc.wait()
            except:
                pass
        del proc

def clean_garbage():
    global RLIMIT_SUPPORTED
    print(f"\n🧹 清理任务开始（{get_elapsed_time()}）")

    temp_files = glob.glob("/tmp/*.ffprobe") + glob.glob("/tmp/ffprobe*") + glob.glob("/tmp/aiohttp*")
    file_count = 0
    for f in temp_files:
        try:
            os.remove(f)
            file_count += 1
        except:
            pass
    print(f"✅ 清理临时文件 {file_count} 个（{get_elapsed_time()}）")

    if os.name == "posix":
        try:
            for proc in psutil.process_iter(['pid', 'cmdline']):
                try:
                    if 'ffprobe' in proc.info['cmdline'] and str(os.getpid()) in ' '.join(proc.info['cmdline']):
                        proc.kill()
                        proc.wait()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            print(f"✅ 清理ffprobe进程完成（{get_elapsed_time()}）")
        except:
            pass

    force_gc()
    print(f"✅ 清理任务完成（{get_elapsed_time()}）\n")

def clean_loop():
    while not STOP_EVENT.wait(CLEAN_INTERVAL):
        clean_garbage()

def init_placeholder():
    """初始化占位文件（兼容iStoreOS，避免删除文件报错）"""
    output_dir = os.path.dirname(OUTPUT_FILE)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    placeholder_content = """努力生成中,#genre#
首次启动需等待,https://kakaxi-1.asia/LOGO/Disclaimer.mp4
请30-60分钟后重试,#genre#
勿急正在快马加鞭,https://kakaxi-1.asia/LOGO/Disclaimer.mp4
"""
    with open(PLACEHOLDER_FILE, "w", encoding="utf-8") as f:
        f.write(placeholder_content)
    
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'w') as f:
                f.truncate(0)
            print(f"📝 清空旧节目单文件完成（{get_elapsed_time()}）")
        except Exception as e:
            print(f"⚠️  清空旧文件失败（不影响启动）：{e}（{get_elapsed_time()}）")
    
    print(f"📝 占位文件初始化完成（{get_elapsed_time()}）")

def generate_json_urls():
    """生成待抓取的JSON接口URL"""
    BASE_URLS = [
        "http://61.156.228.1:8154",
        "http://61.184.46.1:9901",
        "http://120.196.235.1:9901",
        "http://183.215.134.1:19901",
        "http://182.207.218.1:999",
        "http://36.36.200.1:44330",
        "http://111.221.137.1:44330",
        "http://120.238.94.1:9901",
        "http://1.198.30.1:9901",
        "http://1.198.67.1:9901",
        "http://1.199.234.1:9901",
        "http://1.199.235.1:9901",
        "http://101.65.32.1:9901",
        "http://101.66.199.1:9901",
        "http://106.46.34.1:9901",
        "http://106.55.164.1:9901",
        "http://110.189.180.1:9901",
        "http://111.8.224.1:8085",
        "http://112.123.218.1:9901",
        "http://112.123.219.1:9901",
        "http://112.132.160.1:9901",
        "http://112.193.114.1:9901",
        "http://112.234.23.1:9901",
        "http://113.220.232.1:9999",
        "http://113.220.233.1:9999",
        "http://113.220.234.1:9999",
        "http://113.220.235.1:9999",
        "http://113.223.12.1:9998",
        "http://113.236.30.1:9901",
        "http://113.245.217.1:9901",
        "http://113.245.218.1:9901",
        "http://115.207.24.1:9901",
        "http://115.215.143.1:9901",
        "http://115.220.17.1:9901",
        "http://115.224.206.1:9901",
        "http://116.227.232.1:7777",
        "http://116.233.34.1:7777",
        "http://116.30.121.1:8883",
        "http://116.31.165.1:280",
        "http://116.31.165.1:3079",
        "http://118.248.167.1:8088",
        "http://118.248.168.1:8088",
        "http://119.62.36.1:9901",
        "http://119.62.80.1:9901",
        "http://120.0.52.1:8086",
        "http://120.0.8.1:8086",
        "http://120.197.43.1:9901",
        "http://120.198.96.1:9901",
        "http://121.238.176.1:9901",
        "http://121.24.98.1:9901",
        "http://121.33.239.1:9901",
        "http://121.19.134.1:808",
        "http://122.4.92.1:9991",
        "http://123.10.69.1:9901",
        "http://123.10.70.1:9901",
        "http://123.10.71.1:9901",
        "http://123.101.144.1:9901",
        "http://123.183.24.1:6666",
        "http://123.183.25.1:6666",
        "http://123.183.27.1:6666",
        "http://123.189.36.1:9901",
        "http://123.235.8.1:9901",
        "http://123.4.125.1:9901",
        "http://123.52.12.1:9901",
        "http://123.54.171.1:9901",
        "http://123.54.220.1:9901",
        "http://123.55.3.1:9901",
        "http://123.7.110.1:9901",
        "http://123.9.47.1:9901",
        "http://124.238.110.1:9999",
        "http://124.66.82.1:9901",
        "http://124.90.211.1:9901",
        "http://124.94.193.1:9902",
        "http://125.106.86.1:9901",
        "http://125.107.177.1:9901",
        "http://125.107.97.1:9901",
        "http://125.114.210.1:9901",
        "http://125.114.241.1:9901",
        "http://125.115.210.1:9901",
        "http://125.119.48.1:9901",
        "http://125.125.129.1:9901",
        "http://125.125.133.1:9901",
        "http://125.125.134.1:9901",
        "http://125.42.150.1:9901",
        "http://125.42.151.1:9901",
        "http://125.43.240.1:9901",
        "http://125.43.244.1:9901",
        "http://125.43.247.1:9901",
        "http://125.43.249.1:9901",
        "http://150.255.145.1:9901",
        "http://150.255.149.1:9901",
        "http://150.255.150.1:9901",
        "http://150.255.157.1:9901",
        "http://150.255.216.1:9901",
        "http://153.0.204.1:9901",
        "http://163.177.122.1:9901",
        "http://171.104.198.1:8181",
        "http://171.106.217.1:8181",
        "http://171.108.239.1:8181",
        "http://171.12.189.1:9901",
        "http://171.14.89.1:9901",
        "http://171.35.124.1:10011",
        "http://171.38.194.1:8082",
        "http://171.8.75.1:8011",
        "http://180.113.102.1:5000",
        "http://180.117.149.1:9901",
        "http://180.124.146.1:60000",
        "http://180.175.163.1:7777",
        "http://180.213.174.1:9901",
        "http://182.117.136.1:9901",
        "http://182.117.90.1:9901",
        "http://182.120.229.1:9901",
        "http://182.122.122.1:9901",
        "http://182.122.73.1:10086",
        "http://182.125.172.1:9901",
        "http://182.126.114.1:9901",
        "http://183.10.180.1:9901",
        "http://183.10.181.1:9901",
        "http://202.168.187.1:9999",
        "http://210.22.75.1:9901",
        "http://218.13.170.1:9901",
        "http://218.29.147.1:9901",
        "http://218.71.245.1:9901",
        "http://218.74.169.1:9901",
        "http://218.74.171.1:9901",
        "http://220.180.109.1:9902",
        "http://220.180.112.1:9901",
        "http://220.180.229.1:9901",
        "http://220.202.98.1:14901",
        "http://220.248.173.1:9901",
        "http://221.205.131.1:9999",
        "http://221.206.104.1:9901",
        "http://221.213.69.1:9901",
        "http://221.213.94.1:9901",
        "http://222.140.9.1:9901",
        "http://222.142.198.1:9901",
        "http://222.142.72.1:9901",
        "http://222.142.73.1:9901",
        "http://222.142.93.1:9901",
        "http://222.169.70.1:9901",
        "http://222.92.7.1:3334",
        "http://223.151.51.1:9901",
        "http://223.159.11.1:8099",
        "http://223.159.8.1:8099",
        "http://223.159.9.1:8099",
        "http://223.166.234.1:7777",
        "http://223.199.83.1:9901",
        "http://223.241.247.1:9901",
        "http://223.243.10.1:9008",
        "http://36.49.56.1:9901",
        "http://36.99.134.1:9901",
        "http://36.99.206.1:9901",
        "http://39.152.171.1:9901",
        "http://39.164.202.1:8899",
        "http://39.164.222.1:888",
        "http://39.165.44.1:9901",
        "http://39.74.142.1:9999",
        "http://42.225.203.1:9901",
        "http://42.225.222.1:9901",
        "http://42.235.4.1:9901",
        "http://42.237.248.1:9901",
        "http://42.237.26.1:9901",
        "http://49.234.31.1:7033",
        "http://58.20.77.1:9002",
        "http://58.209.101.1:9901",
        "http://58.210.23.1:9901",
        "http://58.210.60.1:9901",
        "http://58.216.229.1:9901",
        "http://58.48.5.1:1111",
        "http://58.51.111.1:1111",
        "http://58.51.111.1:9901",
        "http://58.53.152.1:9901",
        "http://58.57.40.1:9901",
        "http://59.173.183.1:9901",
        "http://59.173.243.1:9901",
        "http://60.187.74.1:9901",
        "http://60.190.18.1:9901",
        "http://60.209.232.1:9901",
        "http://60.213.92.1:9901",
        "http://60.217.73.1:83",
        "http://60.255.137.1:9901",
        "http://60.255.47.1:8801",
        "http://60.255.47.1:9901",
        "http://60.4.9.1:9901",
        "http://61.130.72.1:8888",
        "http://61.136.172.1:9901",
        "http://61.136.67.1:50085",
        "http://61.138.128.1:19901",
    ]
    JSON_PATHS = [
        "/iptv/live/1000.json?key=txiptv",
        "/iptv/live/1001.json?key=txiptv",
    ]

    urls = []
    for base in BASE_URLS:
        try:
            ip_start = base.find("//") + 2
            ip_end = base.find(":", ip_start)
            if ip_end == -1:
                ip = base[ip_start:]
                port = ":80"
            else:
                ip = base[ip_start:ip_end]
                port = base[ip_end:]
            ip_prefix = ip.rsplit(".", 1)[0]
            for i in range(1, 256):
                for path in JSON_PATHS:
                    urls.append(f"http://{ip_prefix}.{i}{port}{path}")
        except Exception as e:
            print(f"⚠️ 解析BASE_URL {base} 失败：{e}")
    if IS_FIRST_RUN:
        original_count = len(urls)
        urls = urls[:FIRST_RUN_LIMIT]
        print(f"⚠️ 首次启动限制接口数量：{len(urls)}/{original_count}（{get_elapsed_time()}）")
    else:
        print(f"📊 生成JSON接口列表完成，共 {len(urls)} 个（{get_elapsed_time()}）")
    return urls

async def generate_itvlist():
    """生成IPTV节目单"""
    global IS_FIRST_RUN
    run_type = "首次启动" if IS_FIRST_RUN else "定时更新"
    print(f"🚀 开始生成节目单（{run_type}）（{get_elapsed_time()}）")

    config = load_channel_config()
    CHANNEL_CATEGORIES = config["categories"]
    CHANNEL_MAPPING = config["mapping"]

    timeout = aiohttp.ClientTimeout(total=30)
    connector = aiohttp.TCPConnector(
        limit=50,
        limit_per_host=10,
        ttl_dns_cache=300,
        enable_cleanup_closed=True
    )

    session = aiohttp.ClientSession(timeout=timeout, connector=connector)

    try:
        urls = generate_json_urls()
        sem = asyncio.Semaphore(JSON_CONCURRENCY)

        async def check(url):
            async with sem:
                try:
                    async with session.get(url, timeout=2) as r:
                        return url if r.status == 200 else None
                except:
                    return None

        valid_urls = [u for u in await asyncio.gather(*[check(u) for u in urls]) if u]
        print(f"✅ 检测到 {len(valid_urls)} 个可用JSON接口（{get_elapsed_time()}）")

        all_channels = []
        sem2 = asyncio.Semaphore(CONCURRENCY)

        async def fetch(u):
            async with sem2:
                try:
                    async with session.get(u, timeout=3) as r:
                        j = await r.json()
                        res = []
                        for x in j.get("data", []):
                            name = x.get("name", "").strip()
                            url = x.get("url", "").strip()
                            if not name or not url or "," in url:
                                continue
                            if not url.startswith("http"):
                                url = urljoin(u, url)
                            res.append((name, url))
                        return res
                except:
                    return []

        for part in await asyncio.gather(*[fetch(u) for u in valid_urls]):
            all_channels.extend(part)

        grouped = {}
        for n, u in all_channels:
            std_name = n.strip().replace("＋", "+").replace("（", "(").replace("）", ")")
            for std, aliases in CHANNEL_MAPPING.items():
                if std_name.lower() in [a.lower() for a in aliases]:
                    std_name = std
                    break
            grouped.setdefault(std_name, []).append(u)
        print(f"✅ 爬取到 {len(grouped)} 个唯一频道（{get_elapsed_time()}）")

        measured = {}
        sem3 = asyncio.Semaphore(FFPROBE_CONCURRENCY)
        processed = 0
        total = len(grouped)

        for ch, urls in grouped.items():
            async def chk(u):
                async with sem3:
                    return u if await probe_has_video(u) else None
            check_urls = urls[:MAX_SOURCES_PER_CHANNEL]
            res = [x for x in await asyncio.gather(*[chk(u) for u in check_urls]) if x]
            if res:
                measured[ch] = res[:MAX_SOURCES_TO_WRITE]
            processed += 1
            if processed % 10 == 0:
                print(f"🔄 检测进度：{processed}/{total}（{get_elapsed_time()}）")

        tz = pytz.timezone('Asia/Shanghai')
        now = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
        tmp_file = OUTPUT_FILE + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            f.write(f"更新时间,#genre#\n{now},https://kakaxi-1.asia/LOGO/Disclaimer.mp4\n\n")
            for cat in CHANNEL_CATEGORIES:
                cl = CHANNEL_CATEGORIES[cat]
                f.write(f"{cat},#genre#\n")
                for c in cl:
                    for s in measured.get(c, []):
                        f.write(f"{c},{s}\n")
                f.write("\n")

        os.replace(tmp_file, OUTPUT_FILE)
        if os.path.exists(PLACEHOLDER_FILE):
            try:
                os.remove(PLACEHOLDER_FILE)
            except Exception as e:
                print(f"⚠️  删除占位文件失败（不影响使用）：{e}")

    finally:
        await safe_session_close(session)

    IS_FIRST_RUN = False
    print(f"✅ {run_type} 生成完成，保留 {len(measured)} 个频道（{get_elapsed_time()}）\n")

def background_loop():
    """后台定时生成节目单"""
    print(f"🔄 节目单更新任务已启动（{get_elapsed_time()}）")
    while not STOP_EVENT.is_set():
        try:
            asyncio.run(generate_itvlist())
            if STOP_EVENT.wait(UPDATE_INTERVAL):
                break
        except Exception as e:
            print(f"❌ 生成节目单异常：{e}（{get_elapsed_time()}）")
            if STOP_EVENT.wait(60):
                break
        force_gc()

app = Flask(__name__)

@app.route("/")
def index():
    """前端配置面板入口"""
    return send_file(os.path.join(os.path.dirname(__file__), "static", "index.html"))

@app.route("/api/config", methods=["GET"])
def get_config():
    """获取分类+映射配置"""
    config = load_channel_config()
    return {
        "code": 200,
        "msg": "success",
        "data": config
    }

@app.route("/api/config", methods=["POST"])
def update_config():
    """保存分类+映射配置"""
    try:
        new_config = request.get_json()
        success, msg = save_channel_config(new_config)
        if success:
            def regenerate():
                try:
                    asyncio.run(generate_itvlist())
                except Exception as e:
                    print(f"❌ 自动更新节目单失败：{e}")
            threading.Thread(target=regenerate, daemon=True).start()
        return {
            "code": 200 if success else 500,
            "msg": msg
        }
    except Exception as e:
        return {
            "code": 500,
            "msg": f"配置解析失败：{str(e)}"
        }

@app.route("/list.txt")
def serve_list():
    """提供节目单访问"""
    if os.path.exists(OUTPUT_FILE):
        response = make_response(send_file(OUTPUT_FILE, mimetype="text/plain"))
        response.headers["Content-Type"] = "text/plain; charset=utf-8"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response
    init_placeholder()
    return fix_placeholder_response()

def fix_placeholder_response():
    """返回占位响应"""
    with open(PLACEHOLDER_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    resp = make_response(content)
    resp.headers["Content-Type"] = "text/plain; charset=utf-8"
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

def handle_exit(signum, frame):
    """优雅退出"""
    print(f"\n📤 收到退出信号，正在停止服务...（{get_elapsed_time()}）")
    STOP_EVENT.set()
    time.sleep(2)
    print(f"✅ 服务已停止（{get_elapsed_time()}）")
    os._exit(0)

if __name__ == "__main__":
    import signal
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    init_config_dir()
    init_placeholder()

    print(f"🌐 Flask服务启动，监听端口：{PORT}（{get_elapsed_time()}）")
    threading.Thread(target=background_loop, daemon=True).start()
    threading.Thread(target=clean_loop, daemon=True).start()
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False,
        threaded=True
    )

