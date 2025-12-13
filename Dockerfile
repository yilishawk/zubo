FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝脚本
COPY iptv_script.py ./

# 暴露端口
EXPOSE 9090

CMD ["python", "iptv_script.py"]
