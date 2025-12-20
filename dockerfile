FROM python:3.10-slim-bullseye

WORKDIR /app

RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list && \
    sed -i 's/security.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list

RUN apt update && apt install -y --no-install-recommends \
    ffmpeg \
    libc6-dev \
    gcc \
    procps \
    vim \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

RUN mkdir -p /app/config && chmod 777 /app/config && chown -R root:root /app

COPY v146.py .
COPY static /app/static

EXPOSE 5000

ENV PORT=5000

CMD ["python", "-u", "-X", "gc_threshold=1000000", "v146.py"]
