FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY v101.py .

RUN pip install --no-cache-dir aiohttp flask

EXPOSE 5000

CMD ["python", "v101.py"]
