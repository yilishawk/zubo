FROM python:3.11-slim

WORKDIR /app

RUN python -m pip install --no-cache-dir \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --trusted-host pypi.tuna.tsinghua.edu.cn \
    aiohttp flask

COPY app.py .

EXPOSE 5000

CMD ["python", "app.py"]
