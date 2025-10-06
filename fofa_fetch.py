import requests
import os

FOFA_EMAIL = os.environ.get("FOFA_EMAIL")
FOFA_KEY = os.environ.get("FOFA_KEY")

if not FOFA_EMAIL or not FOFA_KEY:
    raise ValueError("请设置环境变量 FOFA_EMAIL 和 FOFA_KEY")

cities = ["北京", "河北"]

PAGE_SIZE = 100

for city in cities:
    query = f'country="CN" && city="{city}"'
    url = f'https://fofa.info/api/v1/search/all?email={FOFA_EMAIL}&key={FOFA_KEY}&qbase64={requests.utils.quote(query.encode())}&size={PAGE_SIZE}'

    city_isp_dict = {
        f"{city}电信.txt": set(),
        f"{city}联通.txt": set(),
        f"{city}移动.txt": set(),
    }

    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        results = data.get("results", [])

        for record in results:
            if len(record) < 7:
                continue
            ip = record[0]
            port = record[1]
            isp = record[6]

            if "电信" in isp:
                isp_name = "电信"
            elif "联通" in isp:
                isp_name = "联通"
            elif "移动" in isp:
                isp_name = "移动"
            else:
                continue  

            filename = f"{city}{isp_name}.txt"
            city_isp_dict[filename].add(f"{ip}:{port}")

        for filename, ip_set in city_isp_dict.items():
            with open(filename, "w", encoding="utf-8") as f:
                for ip_port in sorted(ip_set):
                    f.write(ip_port + "\n")

        print(f"{city} IP抓取完成，共生成 {len(city_isp_dict)} 个文件。")

    except Exception as e:
        print(f"{city} 抓取失败：{e}")
        for filename in city_isp_dict.keys():
            with open(filename, "w", encoding="utf-8"):
                pass
