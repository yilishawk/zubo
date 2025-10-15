import os
import re
import time
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

# ===== 配置部分 =====
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(REPO_DIR, "IPTV.txt")
IP_DIR = os.path.join(REPO_DIR, "ip")
RTP_DIR = os.path.join(REPO_DIR, "rtp")
os.makedirs(IP_DIR, exist_ok=True)

ROUND_FILE = os.path.join(REPO_DIR, "round.txt")

# ===== 频道映射与分类 =====
CHANNEL_CATEGORIES = {
    "央视频道": ["CCTV1", "CCTV2"],
    "卫视频道": ["湖南卫视", "浙江卫视"],
    "数字频道": ["CHC动作电影", "CHC家庭影院", "CHC影迷电影"]
}

CHANNEL_MAPPING = {
    "CCTV1": ["CCTV-1", "CCTV-1 HD", "CCTV1 HD", "CCTV-1综合", "CCTV1 4M1080", "CCTV1 5M1080HEVC"],
    "CCTV2": ["CCTV-2", "CCTV-2 HD", "CCTV2 HD", "CCTV-2财经"],
    "湖南卫视": ["湖南", "湖南HD", "湖南卫视高清"],
    "浙江卫视": ["浙江", "浙江HD", "浙江卫视高清"],
    "CHC动作电影": ["CHC动作", "CHC动作HD"],
    "CHC家庭影院": ["CHC家庭", "CHC家庭HD"],
    "CHC影迷电影": ["CHC影迷", "CHC影迷HD"]
}

# ===== 工具函数 =====
def get_round():
    if os.path.exists(ROUND_FILE):
        with open(ROUND_FILE, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    return 0


def save_round(n):
    with open(ROUND_FILE, "w", encoding="utf-8") as f:
        f.write(str(n))


def check_stream_playable(url, timeout=5):
    """使用 ffprobe 检测 IPTV 源是否可播放"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-timeout", str(timeout * 1000000), "-i", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout + 2
        )
        return b"Stream #" in result.stderr
    except Exception:
        return False


def map_channel(name):
    """将频道名称映射为规范化名称"""
    for std_name, aliases in CHANNEL_MAPPING.items():
        for alias in aliases:
            if alias.lower() in name.lower():
                return std_name
    return name.strip()


# ===== 第一阶段 =====
def fetch_ip_list():
    """读取 IP_DIR 下的所有 IP 文件"""
    ips = []
    for fname in os.listdir(IP_DIR):
        if fname.endswith(".txt"):
            path = os.path.join(IP_DIR, fname)
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    ip = line.strip()
                    if ip:
                        ips.append((ip, fname.replace(".txt", "")))  # (IP, 省份运营商)
    print(f"✅ 第一阶段完成，共 {len(ips)} 个 IP")
    return ips


# ===== 第二阶段 =====
def detect_channels(ips):
    """检测每个 IP 的 CCTV1 是否可播，保留可播 IP 的全部频道"""
    valid_entries = []

    def process_ip(ip_tuple):
        ip, province_operator = ip_tuple
        rtp_file = os.path.join(RTP_DIR, f"{province_operator}.txt")
        if not os.path.exists(rtp_file):
            return []

        channels = []
        with open(rtp_file, "r", encoding="utf-8") as f:
            for line in f:
                if "," in line:
                    ch_name, rtp_url = line.strip().split(",", 1)
                    channels.append((ch_name, rtp_url))

        # CCTV1 检测
        cctv1_urls = [f"http://{ip}/rtp/{url.split('rtp://')[1]}" for ch, url in channels if "CCTV1" in ch]
        if not any(check_stream_playable(u) for u in cctv1_urls):
            print(f"🚫 {province_operator} {ip} 全部 CCTV1 不可播放，跳过")
            return []

        # CCTV1 可播，保留全部频道并加编号后缀
        ip_entries = []
        for idx, (ch_name, rtp_url) in enumerate(channels, start=1):
            full_url = f"http://{ip}/rtp/{rtp_url.split('rtp://')[1]}${province_operator}{idx}"
            ip_entries.append((ch_name, full_url))
        print(f"✅ {province_operator} {ip} 可播放，保留全部频道")
        return ip_entries

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_ip, ip_tuple) for ip_tuple in ips]
        for future in as_completed(futures):
            valid_entries.extend(future.result())

    return valid_entries


def classify_and_save(entries):
    """分类并生成 IPTV.txt"""
    category_map = {cat: [] for cat in CHANNEL_CATEGORIES.keys()}

    for ch_name, url in entries:
        mapped = map_channel(ch_name)
        for cat, keywords in CHANNEL_CATEGORIES.items():
            if mapped in keywords:
                category_map[cat].append(f"{mapped},{url}")
                break

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for cat, lines in category_map.items():
            f.write(f"{cat},#genre#\n")
            for line in sorted(set(lines)):
                f.write(f"{line}\n")
            f.write("\n")

    print(f"🎯 第二阶段完成，已生成 IPTV.txt，共 {len(entries)} 条频道")


def push_to_repo():
    """推送 IPTV.txt 到仓库"""
    os.system('git config --global user.email "actions@github.com"')
    os.system('git config --global user.name "github-actions"')
    os.system("git add IPTV.txt")
    now_round = get_round() + 1
    os.system(f'git commit -m "自动更新 IPTV.txt（第 {now_round} 次）" || echo "nothing to commit"')
    os.system("git push")
    save_round(now_round)
    print("🚀 已推送 IPTV.txt 到仓库")


# ===== 主流程 =====
if __name__ == "__main__":
    print("="*50)
    print("▶ IPTV 自动更新脚本（ffprobe检测版 + 编号后缀）")
    print("="*50)

    ips = fetch_ip_list()
    if not ips:
        print("❌ 没有可用IP，结束任务。")
        exit()

    valid_entries = detect_channels(ips)
    classify_and_save(valid_entries)
    push_to_repo()