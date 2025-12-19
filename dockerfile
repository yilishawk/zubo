FROM python:3.10-slim-bullseye

WORKDIR /app

RUN apt update && apt install -y --no-install-recommends \
    ffmpeg \
    libc6-dev \
    gcc \
    procps \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY v145.py .

EXPOSE 5000

CMD ["python", "-u", "-X", "gc_threshold=1000000", "v145.py"]
