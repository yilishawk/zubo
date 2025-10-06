import requests
import os

# 从环境变量读取 FOFA 邮箱和 API KEY（避免明文写在脚本里）
FOFA_EMAIL = os.environ.get("FOFA_EMAIL")
FOFA_KEY = os.environ.get("FOFA_KEY")

# 指定抓取的城市列表
cities = ["北京", "湖北", "贵州", "湖南", "河北"]

# 每页抓取数量
PAGE_SIZE = 100

# 遍历城市抓取
for city in cities:
    query = f'country="CN" && city="{city}"'
    url = f'https://fofa.info/api/v1/search/all?email={FOFA_EMAIL}&key={FOFA_KEY}&qbase64={requests.utils.quote(query.encode())}&size={PAGE_SIZE}'

    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        results = data.get("results", [])

        # 存储城市+运营商分类的 IP
        city_isp_dict = {}

        for record in results:
            ip = record[0]
            port = record[1]
            isp = record[6]  # 运营商字段

            # 简化运营商名，只保留电信/联通/移动
            if "电信" in isp:
                isp_name = "电信"
            elif "联通" in isp:
                isp_name = "联通"
            elif "移动" in isp:
                isp_name = "移动"
            else:
                isp_name = "其他"

            filename = f"{city}{isp_name}.txt"
            if filename not in city_isp_dict:
                city_isp_dict[filename] = set()
            city_isp_dict[filename].add(f"{ip}:{port}")

        # 写入文件（覆盖原文件）
        for filename, ip_set in city_isp_dict.items():
            with open(filename, "w", encoding="utf-8") as f:
                for ip_port in sorted(ip_set):
                    f.write(ip_port + "\n")

        print(f"{city} IP抓取完成，共生成 {len(city_isp_dict)} 个文件。")

    except Exception as e:
        print(f"{city} 抓取失败：{e}")
