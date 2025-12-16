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
from urllib.parse import urljoin
from flask import Flask, send_file, Response

# ================= 核心配置 =================
PORT = 5000
UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", 21600))
OUTPUT_FILE = "/app/list.txt"
PLACEHOLDER_FILE = "/app/list_placeholder.txt"
CONCURRENCY = 80
JSON_CONCURRENCY = 60
FFPROBE_CONCURRENCY = 4
MAX_SOURCES_PER_CHANNEL = 15
FFPROBE_TIMEOUT = 10
CLEAN_ZOMBIE_INTERVAL = 10800

BASE_URLS = [
    "http://61.156.228.1:8154",
    "http://61.184.46.1:9901",
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

CHANNEL_CATEGORIES = {
    "央视频道": [
        "CCTV1", "CCTV2", "CCTV3", "CCTV4", "CCTV4欧洲", "CCTV4美洲", "CCTV5", "CCTV5+", "CCTV6", "CCTV7",
        "CCTV8", "CCTV9", "CCTV10", "CCTV11", "CCTV12", "CCTV13", "CCTV14", "CCTV15", "CCTV16", "CCTV17",
        "兵器科技", "风云音乐", "风云足球", "风云剧场", "怀旧剧场", "第一剧场", "女性时尚", "世界地理", "央视台球", "高尔夫网球",
        "央视文化精品", "卫生健康", "电视指南", "老故事", "中学生", "发现之旅", "书法频道", "国学频道", "环球奇观"
    ],
    "卫视频道": [
        "湖南卫视", "浙江卫视", "江苏卫视", "东方卫视", "深圳卫视", "北京卫视", "广东卫视", "广西卫视", "东南卫视", "海南卫视",
        "河北卫视", "河南卫视", "湖北卫视", "江西卫视", "四川卫视", "重庆卫视", "贵州卫视", "云南卫视", "天津卫视", "安徽卫视",
        "山东卫视", "辽宁卫视", "黑龙江卫视", "吉林卫视", "内蒙古卫视", "宁夏卫视", "山西卫视", "陕西卫视", "甘肃卫视", "青海卫视",
        "新疆卫视", "西藏卫视", "三沙卫视", "兵团卫视", "延边卫视", "安多卫视", "康巴卫视", "农林卫视", "山东教育卫视",
        "中国教育1台", "中国教育2台", "中国教育3台", "中国教育4台", "早期教育"
    ],
    "数字频道": [
        "CHC动作电影", "CHC家庭影院", "CHC影迷电影", "淘电影", "淘精彩", "淘剧场", "淘4K", "淘娱乐", "淘BABY", "淘萌宠", "重温经典",
        "星空卫视", "CHANNELV", "凤凰卫视中文台", "凤凰卫视资讯台", "凤凰卫视香港台", "凤凰卫视电影台", "求索纪录", "求索科学",
        "求索生活", "求索动物", "纪实人文", "金鹰纪实", "纪实科教", "睛彩青少", "睛彩竞技", "睛彩篮球", "睛彩广场舞", "魅力足球", "五星体育",
        "劲爆体育", "快乐垂钓", "茶频道", "先锋乒羽", "天元围棋", "汽摩", "梨园频道", "文物宝库", "武术世界",
        "乐游", "生活时尚", "都市剧场", "欢笑剧场", "游戏风云", "金色学堂", "动漫秀场", "新动漫", "卡酷少儿", "金鹰卡通", "优漫卡通", "哈哈炫动", "嘉佳卡通", 
        "中国交通", "中国天气"
    ],
}

CHANNEL_MAPPING = {
    "CCTV1": ["CCTV-1", "CCTV1-综合", "CCTV-1 综合", "CCTV-1综合", "CCTV1HD", "CCTV-1高清", "CCTV-1HD", "cctv-1HD", "CCTV1综合高清", "cctv1"],
    "CCTV2": ["CCTV-2", "CCTV2-财经", "CCTV-2 财经", "CCTV-2财经", "CCTV2HD", "CCTV-2高清", "CCTV-2HD", "cctv-2HD", "CCTV2财经高清", "cctv2"],
    "CCTV3": ["CCTV-3", "CCTV3-综艺", "CCTV-3 综艺", "CCTV-3综艺", "CCTV3HD", "CCTV-3高清", "CCTV-3HD", "cctv-3HD", "CCTV3综艺高清", "cctv3"],
    "CCTV4": ["CCTV-4", "CCTV4-国际", "CCTV-4 中文国际", "CCTV-4中文国际", "CCTV4HD", "cctv4HD", "CCTV-4HD", "cctv-4HD", "CCTV4国际高清", "cctv4"],
    "CCTV4欧洲": ["CCTV-4欧洲", "CCTV-4欧洲", "CCTV4欧洲 HD", "CCTV-4 欧洲", "CCTV-4中文国际欧洲", "CCTV4中文欧洲", "CCTV4欧洲HD", "cctv4欧洲HD", "CCTV-4欧洲HD", "cctv-4欧洲HD"],
    "CCTV4美洲": ["CCTV-4美洲", "CCTV-4北美", "CCTV4美洲 HD", "CCTV-4 美洲", "CCTV-4中文国际美洲", "CCTV4中文美洲", "CCTV4美洲HD", "cctv4美洲HD", "CCTV-4美洲HD", "cctv-4美洲HD"],
    "CCTV5": ["CCTV-5", "CCTV5-体育", "CCTV-5 体育", "CCTV-5体育", "CCTV5HD", "CCTV-5高清", "CCTV-5HD", "cctv-5HD", "CCTV5体育高清", "cctv5"],
    "CCTV5+": ["CCTV-5+", "CCTV-5+ HD", "CCTV-5+ 体育赛事", "CCTV5+体育赛事", "CCTV5+HD", "CCTV-5+高清", "CCTV-5+HD", "cctv-5+HD", "CCTV5plas", "CCTV5+体育赛视高清", "cctv5+"],
    "CCTV6": ["CCTV-6", "CCTV6-电影", "CCTV-6 电影", "CCTV-6电影", "CCTV6HD", "CCTV-6高清", "CCTV-6HD", "cctv-6HD", "CCTV6电影高清", "cctv6"],
    "CCTV7": ["CCTV-7", "CCTV7-军农", "CCTV-7 国防军事", "CCTV-7国防军事", "CCTV7HD", "CCTV-7高清", "CCTV-7HD", "cctv-7HD", "CCTV7军事高清", "cctv7"],
    "CCTV8": ["CCTV-8", "CCTV8-电视剧", "CCTV-8 电视剧", "CCTV-8电视剧", "CCTV8HD", "CCTV-8高清", "CCTV-8HD", "cctv-8HD", "CCTV8电视剧高清", "cctv8"],
    "CCTV9": ["CCTV-9", "CCTV9-纪录", "CCTV-9 纪录", "CCTV-9纪录", "CCTV9HD", "cctv9HD", "CCTV-9高清", "cctv-9HD", "CCTV9记录高清", "cctv9"],
    "CCTV10": ["CCTV-10", "CCTV10-科教", "CCTV-10 科教", "CCTV-10科教", "CCTV10HD", "CCTV-10高清", "CCTV-10HD", "cctv-10HD", "CCTV10科教高清", "cctv10"],
    "CCTV11": ["CCTV-11", "CCTV11-戏曲", "CCTV-11 戏曲", "CCTV-11戏曲", "CCTV11HD", "cctv11HD", "CCTV-11HD", "cctv-11HD", "CCTV11戏曲高清", "cctv11"],
    "CCTV12": ["CCTV-12", "CCTV12-社会与法", "CCTV-12 社会与法", "CCTV-12社会与法", "CCTV12HD", "CCTV-12高清", "CCTV-12HD", "cctv-12HD", "CCTV12社会与法高清", "cctv12"],
    "CCTV13": ["CCTV-13", "CCTV13-新闻", "CCTV-13 新闻", "CCTV-13新闻", "CCTV13HD", "cctv13HD", "CCTV-13HD", "cctv-13HD", "CCTV13新闻高清", "cctv13"],
    "CCTV14": ["CCTV-14", "CCTV14-少儿", "CCTV-14 少儿", "CCTV-14少儿", "CCTV14HD", "CCTV-14高清", "CCTV-14HD", "cctv-14HD", "CCTV14少儿高清", "cctv14"],
    "CCTV15": ["CCTV-15", "CCTV15-音乐", "CCTV-15 音乐", "CCTV-15音乐", "CCTV15HD", "cctv15HD", "CCTV-15HD", "cctv-15HD", "CCTV15音乐高清", "cctv15"],
    "CCTV16": ["CCTV-16", "CCTV-16 HD", "CCTV-16 4K", "CCTV-16奥林匹克", "CCTV16HD", "cctv16HD", "CCTV-16HD", "cctv-16HD", "CCTV16奥林匹克高清", "cctv16"],
    "CCTV17": ["CCTV-17", "CCTV17高清", "CCTV17 HD", "CCTV-17农业农村", "CCTV17HD", "cctv17HD", "CCTV-17HD", "cctv-17HD", "CCTV17农业农村高清", "cctv17"],
    "兵器科技": ["CCTV-兵器科技", "CCTV兵器科技", "CCTV兵器科技HD"],
    "风云音乐": ["CCTV-风云音乐", "CCTV风云音乐", "CCTV风云音乐HD"],
    "第一剧场": ["CCTV-第一剧场", "CCTV第一剧场", "CCTV第一剧场HD"],
    "风云足球": ["CCTV-风云足球", "CCTV风云足球", "CCTV风云足球HD"],
    "风云剧场": ["CCTV-风云剧场", "CCTV风云剧场", "CCTV风云剧场HD"],
    "怀旧剧场": ["CCTV-怀旧剧场", "CCTV怀旧剧场", "CCTV怀旧剧场HD"],
    "女性时尚": ["CCTV-女性时尚", "CCTV女性时尚", "CCTV女性时尚HD"],
    "世界地理": ["CCTV-世界地理", "CCTV世界地理", "CCTV世界地理HD"],
    "央视台球": ["CCTV-央视台球", "CCTV央视台球", "CCTV央视台球HD"],
    "高尔夫网球": ["CCTV-高尔夫网球", "CCTV高尔夫网球", "CCTV央视高网", "CCTV-高尔夫·网球", "央视高网"],
    "央视文化精品": ["CCTV-央视文化精品", "CCTV央视文化精品", "CCTV文化精品", "CCTV-文化精品", "文化精品"],
    "卫生健康": ["CCTV-卫生健康", "CCTV卫生健康"],
    "电视指南": ["CCTV-电视指南", "CCTV电视指南"],
    "农林卫视": ["陕西农林卫视"],
    "内蒙古卫视": ["内蒙古", "内蒙卫视"],
    "康巴卫视": ["四川康巴卫视"],
    "山东教育卫视": ["山东教育"],
    "中国教育1台": ["CETV1", "中国教育一台", "中国教育1", "CETV", "CETV-1", "中国教育"],
    "中国教育2台": ["CETV2", "中国教育二台", "中国教育2", "CETV-2 空中课堂", "CETV-2"],
    "中国教育3台": ["CETV3", "中国教育三台", "中国教育3", "CETV-3 教育服务", "CETV-3"],
    "中国教育4台": ["CETV4", "中国教育四台", "中国教育4", "中国教育电视台第四频道", "CETV-4"],
    "东南卫视": ["福建东南"],
    "CHC动作电影": ["CHC动作电影高清"],
    "CHC家庭影院": ["CHC家庭电影高清"],
    "CHC影迷电影": ["CHC高清电影", "CHC-影迷电影", "影迷电影", "chc高清电影"],
    "淘电影": ["IPTV淘电影", "北京IPTV淘电影", "北京淘电影"],
    "淘精彩": ["IPTV淘精彩", "北京IPTV淘精彩", "北京淘精彩"],
    "淘剧场": ["IPTV淘剧场", "北京IPTV淘剧场", "北京淘剧场"],
    "淘4K": ["IPTV淘4K", "北京IPTV4K超清", "北京淘4K", "淘4K", "淘 4K"],
    "淘娱乐": ["IPTV淘娱乐", "北京IPTV淘娱乐", "北京淘娱乐"],
    "淘BABY": ["IPTV淘BABY", "北京IPTV淘BABY", "北京淘BABY", "IPTV淘baby", "北京IPTV淘baby", "北京淘baby"],
    "淘萌宠": ["IPTV淘萌宠", "北京IPTV萌宠TV", "北京淘萌宠"],
    "魅力足球": ["上海魅力足球"],
    "睛彩青少": ["睛彩羽毛球"],
    "求索纪录": ["求索记录", "求索纪录4K", "求索记录4K", "求索纪录 4K", "求索记录 4K"],
    "金鹰纪实": ["湖南金鹰纪实", "金鹰记实"],
    "纪实科教": ["北京纪实科教", "BRTV纪实科教", "北京纪实卫视高清"],
    "星空卫视": ["星空衛視", "星空衛视", "星空卫視"],
    "CHANNELV": ["Channel [V]", "Channel[V]"],
    "凤凰卫视中文台": ["凤凰中文", "凤凰中文台", "凤凰卫视中文", "凤凰卫视"],
    "凤凰卫视香港台": ["凤凰香港台", "凤凰卫视香港", "凤凰香港"],
    "凤凰卫视资讯台": ["凤凰资讯", "凤凰资讯台", "凤凰咨询", "凤凰咨询台", "凤凰卫视咨询台", "凤凰卫视资讯", "凤凰卫视咨询"],
    "凤凰卫视电影台": ["凤凰电影", "凤凰电影台", "凤凰卫视电影", "鳳凰衛視電影台", "凤凰电影"],
    "茶频道": ["湖南茶频道", "湖南茶频道高清", "茶频道高清"],
    "快乐垂钓": ["湖南快乐垂钓", "湖南快乐垂钓高清", "快乐垂钓高清"],
    "先锋乒羽": ["湖南先锋乒羽"],
    "天元围棋": ["天元围棋频道"],
    "汽摩": ["重庆汽摩", "汽摩频道", "重庆汽摩频道"],
    "梨园频道": ["河南梨园频道", "梨园", "河南梨园"],
    "文物宝库": ["河南文物宝库"],
    "武术世界": ["河南武术世界"],
    "乐游": ["乐游频道", "上海乐游频道", "乐游纪实", "SiTV乐游频道", "乐游高清"],
    "欢笑剧场": ["上海欢笑剧场4K", "欢笑剧场 4K", "欢笑剧场高清", "上海欢笑剧场"],
    "生活时尚": ["生活时尚4K", "SiTV生活时尚", "上海生活时尚", "生活时尚高清"],
    "都市剧场": ["都市剧场4K", "SiTV都市剧场", "上海都市剧场", "都市剧场高清"],
    "游戏风云": ["游戏风云4K", "SiTV游戏风云", "上海游戏风云", "游戏风云高清"],
    "金色学堂": ["金色学堂4K", "SiTV金色学堂", "上海金色学堂", "金色学堂高清"],
    "动漫秀场": ["动漫秀场4K", "SiTV动漫秀场", "上海动漫秀场", "动漫秀场高清"],
    "卡酷少儿": ["北京KAKU少儿", "BRTV卡酷少儿", "北京卡酷少儿", "卡酷动画", "北京卡通", "北京少儿"],
    "哈哈炫动": ["炫动卡通", "上海哈哈炫动"],
    "优漫卡通": ["江苏优漫卡通", "优漫漫画"],
    "金鹰卡通": ["湖南金鹰卡通"],
    "嘉佳卡通": ["佳佳卡通"],
    "中国交通": ["中国交通频道", "中国交通HD"],
    "中国天气": ["中国天气频道", "中国天气HD"],
}

app = Flask(__name__)

def init_placeholder():
    """创建占位节目单，避免返回空文件"""
    placeholder_content = """更新时间,#genre#
节目单生成中，请30-60分钟后重试,#genre#

等待提示,#genre#
快马加鞭生成中（首次启动需等待约30-60分钟）,https://kakaxi-1.asia/LOGO/Disclaimer.mp4
请稍后重试,https://kakaxi-1.asia/LOGO/Disclaimer.mp4
"""
    os.makedirs(os.path.dirname(PLACEHOLDER_FILE), exist_ok=True)
    with open(PLACEHOLDER_FILE, "w", encoding="utf-8") as f:
        f.write(placeholder_content)
    if os.path.exists(OUTPUT_FILE):
        try:
            os.remove(OUTPUT_FILE)
        except:
            pass
    print("✅ 占位文件初始化完成")

def clean_zombie_processes():
    """清理僵尸进程，释放内存和PID"""
    try:
        zombie_count = 0
        for proc in psutil.process_iter(['pid', 'status', 'name']):
            try:
                if proc.info['status'] == psutil.STATUS_ZOMBIE:
                    proc.kill()
                    zombie_count += 1
                    print(f"🗑️ 清理僵尸进程 - PID: {proc.info['pid']}, 名称: {proc.info.get('name', '未知')}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        if zombie_count > 0:
            print(f"✅ 共清理 {zombie_count} 个僵尸进程")
        else:
            print("ℹ️ 未检测到僵尸进程")
    except Exception as e:
        print(f"⚠️ 清理僵尸进程失败: {str(e)}")

def clean_temp_files():
    """清理临时文件，释放磁盘空间"""
    temp_files = [
        OUTPUT_FILE + ".tmp",
        PLACEHOLDER_FILE,
        "/tmp/ffprobe*",
        "/app/*.tmp"
    ]
    cleaned_count = 0
    for temp_file in temp_files:
        try:
            if "*" in temp_file:
                import glob
                for f in glob.glob(temp_file):
                    os.remove(f)
                    cleaned_count += 1
            elif os.path.exists(temp_file):
                os.remove(temp_file)
                cleaned_count += 1
        except:
            continue
    print(f"✅ 清理临时文件完成，共删除 {cleaned_count} 个文件")

def is_valid_stream(url: str) -> bool:
    """验证流地址是否有效"""
    if url.startswith(("rtp://", "udp://", "rtsp://")):
        return False
    if any(x in url for x in ("239.", "/paiptv/", "/00/SNM/", "/00/CHANNEL")):
        return False
    return any(ext in url for ext in (".m3u8", ".ts", ".flv", ".mp4"))

def normalize_name(name: str) -> str:
    """标准化频道名称，过滤广播/音频频道"""
    n = name.strip()
    n = n.replace("＋", "+").replace("（", "(").replace("）", ")")
    
    exclude_keywords = ["广播", "音频", "电台", "FM", "AM", "音乐台", "有声"]
    if any(keyword in n for keyword in exclude_keywords):
        return ""
    
    for std, aliases in CHANNEL_MAPPING.items():
        for a in aliases:
            a2 = a.replace("＋", "+").replace("（", "(").replace("）", ")")
            if n.lower() == a2.lower():
                return std
    return n

def generate_json_urls():
    """生成待爬取的JSON URL列表"""
    urls = []
    for base in BASE_URLS:
        try:
            ip_start = base.find("//") + 2
            ip_end = base.find(":", ip_start)
            base_url = base[:ip_start]
            prefix = base[ip_start:ip_end].rsplit(".", 1)[0]
            port = base[ip_end:]

            for i in range(1, 256):
                for path in JSON_PATHS:
                    urls.append(f"{base_url}{prefix}.{i}{port}{path}")
        except:
            continue
    return urls

def group_by_channel(channels):
    """按频道分组"""
    grouped = {}
    for name, url in channels:
        if name:
            grouped.setdefault(name, []).append(url)
    return grouped

# ================= 异步函数 =================
async def check_json(session, url, sem):
    """检查JSON接口是否可用"""
    async with sem:
        try:
            async with session.get(url, timeout=2, verify_ssl=False) as r:
                return url if r.status == 200 else None
        except:
            return None

async def fetch_channels(session, url, sem):
    """爬取频道列表"""
    async with sem:
        try:
            async with session.get(url, timeout=3, verify_ssl=False) as r:
                data = await r.json()
                result = []
                for item in data.get("data", []):
                    name = item.get("name", "")
                    u = item.get("url", "")
                    if not name or not u or "," in u:
                        continue
                    if not u.startswith("http"):
                        u = urljoin(url, u)
                    norm_name = normalize_name(name)
                    if norm_name and is_valid_stream(u):
                        result.append((norm_name, u))
                return result
        except:
            return []

async def probe_speed(url, sem):
    """检测流是否包含有效视频流，并返回测速结果"""
    async with sem:
        start = time.time()
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffprobe",
                "-v", "error",
                "-show_entries", "stream=codec_type,width,height",
                "-of", "json",
                "-i", url,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=FFPROBE_TIMEOUT)

            if proc.returncode != 0:
                return None
            
            ffprobe_data = json.loads(stdout.decode('utf-8', errors='ignore'))
            streams = ffprobe_data.get("streams", [])
            
            has_valid_video = False
            for stream in streams:
                if stream.get("codec_type") == "video":
                    width = stream.get("width", 0)
                    height = stream.get("height", 0)
                    if width > 0 and height > 0:
                        has_valid_video = True
                        break
            
            if has_valid_video:
                return time.time() - start
            else:
                print(f"❌ 过滤纯音频流: {url}")
                return None
        except Exception as e:
            return None

async def measure_channel_sources(channel_dict):
    """检测频道源的有效性"""
    sem = asyncio.Semaphore(FFPROBE_CONCURRENCY)
    measured = {}

    for name, urls in channel_dict.items():
        urls = urls[:MAX_SOURCES_PER_CHANNEL]
        tasks = [probe_speed(u, sem) for u in urls]
        speeds = await asyncio.gather(*tasks)
        valid = [
            (u, s) for u, s in zip(urls, speeds)
            if s is not None
        ]
        valid.sort(key=lambda x: x[1])
        if valid:
            measured[name] = [v[0] for v in valid]
    
    return measured

async def generate_itvlist():
    """生成最终的节目单"""
    clean_temp_files()
    
    timeout = aiohttp.ClientTimeout(total=600)
    async with aiohttp.ClientSession(timeout=timeout, verify_ssl=False) as session:
        json_urls = generate_json_urls()
        sem_json = asyncio.Semaphore(JSON_CONCURRENCY)
        json_tasks = [check_json(session, url, sem_json) for url in json_urls]
        valid_json_urls = [u for u in await asyncio.gather(*json_tasks) if u]
        print(f"✅ 检测到 {len(valid_json_urls)} 个可用的JSON接口")

        sem_fetch = asyncio.Semaphore(CONCURRENCY)
        fetch_tasks = [fetch_channels(session, url, sem_fetch) for url in valid_json_urls]
        all_channels = []
        for channels in await asyncio.gather(*fetch_tasks):
            all_channels.extend(channels)
        unique_channels = list({(n, u) for n, u in all_channels})
        print(f"✅ 爬取到 {len(unique_channels)} 个唯一频道")

        channel_dict = group_by_channel(unique_channels)
        measured = await measure_channel_sources(channel_dict)
        print(f"✅ 有效频道源检测完成，保留 {len(measured)} 个频道")

        now = datetime.datetime.now(datetime.timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
        tmp_file = OUTPUT_FILE + ".tmp"
        
        with open(tmp_file, "w", encoding="utf-8") as f:
            f.write(f"更新时间,#genre#\n")
            f.write(f"{now},https://kakaxi-1.asia/LOGO/Disclaimer.mp4\n\n")
            
            for cat, channel_list in CHANNEL_CATEGORIES.items():
                f.write(f"{cat},#genre#\n")
                for channel in channel_list:
                    if channel in measured and measured[channel]:
                        f.write(f"{channel},{measured[channel][0]}\n")
                f.write("\n")
        
        os.replace(tmp_file, OUTPUT_FILE)
        print(f"✅ 节目单生成完成: {OUTPUT_FILE}")
        
        if os.path.exists(PLACEHOLDER_FILE):
            os.remove(PLACEHOLDER_FILE)
    
    return True

# ================= 后台任务 =================
def background_loop():
    """后台循环任务：生成节目单 + 定期清理"""
    first_run = True
    clean_counter = 0
    
    while True:
        try:
            if clean_counter >= CLEAN_ZOMBIE_INTERVAL:
                clean_zombie_processes()
                clean_counter = 0
            
            if first_run:
                print("🚀 首次启动，开始生成节目单...")
                first_run = False
                asyncio.run(generate_itvlist())
            else:
                print(f"🚀 定期更新，距离上次生成已过 {UPDATE_INTERVAL/3600} 小时")
                asyncio.run(generate_itvlist())
            
            for i in range(UPDATE_INTERVAL):
                time.sleep(1)
                clean_counter += 1
        
        except Exception as e:
            print(f"⚠️ 后台任务异常: {str(e)}")
            if not os.path.exists(PLACEHOLDER_FILE):
                init_placeholder()
            time.sleep(60)

# ================= Flask接口 =================
@app.route("/list.txt")
def serve_list():
    """提供节目单访问接口"""
    if os.path.exists(OUTPUT_FILE):
        return send_file(OUTPUT_FILE, mimetype="text/plain")
    else:
        return send_file(PLACEHOLDER_FILE, mimetype="text/plain")

# ================= 主函数 =================
if __name__ == "__main__":
    init_placeholder()
    
    bg_thread = threading.Thread(target=background_loop, daemon=True)
    bg_thread.start()
    print("✅ 后台任务线程已启动")
    
    print(f"🌐 Flask服务启动，监听端口 {PORT}")
    print(f"ℹ️ 当前返回占位节目单，真实节目单正在后台生成")
    
    try:
        app.run(
            host="0.0.0.0",
            port=PORT,
            threaded=True,
            debug=False
        )
    except Exception as e:
        print(f"⚠️ Flask启动失败: {str(e)}")
        while True:
            time.sleep(3600)
