FROM python:3.11-slim

WORKDIR /app

COPY v132.py .

RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir flask aiohttp

ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["python", "v132.py"]
