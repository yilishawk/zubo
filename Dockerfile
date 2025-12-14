FROM python:3.11-slim

RUN echo "nameserver 114.114.114.114" > /etc/resolv.conf

WORKDIR /app

RUN python -m pip install --upgrade pip

RUN python -m pip install --no-cache-dir \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    aiohttp flask

COPY app.py .

EXPOSE 5000

CMD ["python", "app.py"]
