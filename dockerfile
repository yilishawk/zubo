FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y ffmpeg && \
    pip install --no-cache-dir aiohttp flask && \
    rm -rf /var/lib/apt/lists/*

COPY v101.py .

EXPOSE 5000

CMD ["python", "v101.py"]
