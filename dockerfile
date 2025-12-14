FROM python:3.11-slim

WORKDIR /app

COPY v101.py .

RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir flask aiohttp

ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["python", "v101.py"]