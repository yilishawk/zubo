FROM python:3.11-slim

WORKDIR /app

# 复制依赖文件（可选：如果有 requirements.txt）
# COPY requirements.txt .

RUN python -m pip install --no-cache-dir \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --trusted-host pypi.tuna.tsinghua.edu.cn \
    flask aiohttp gunicorn
    
COPY . .

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
