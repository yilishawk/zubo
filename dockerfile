FROM python:3.10-slim-bullseye

WORKDIR /app

RUN echo "deb http://mirrors.aliyun.com/debian/ bullseye main contrib non-free" > /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian/ bullseye-updates main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security/ bullseye-security main contrib non-free" >> /etc/apt/sources.list && \
    apt update && apt install -y --no-install-recommends \
    ffmpeg \
    libc6-dev \
    gcc \
    procps \
    vim \
    libffi-dev \
    libssl-dev \
    python3-dev \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    mkdir -p ~/.pip && \
    echo "[global]" > ~/.pip/pip.conf && \
    echo "index-url = https://pypi.tuna.tsinghua.edu.cn/simple" >> ~/.pip/pip.conf && \
    echo "extra-index-url = https://mirrors.aliyun.com/pypi/simple/ https://pypi.org/simple/" >> ~/.pip/pip.conf && \
    echo "trusted-host = pypi.tuna.tsinghua.edu.cn mirrors.aliyun.com pypi.org files.pythonhosted.org" >> ~/.pip/pip.conf

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/config && chmod 777 /app/config && chown -R root:root /app

COPY v146.py .
COPY static /app/static

EXPOSE 5000
ENV PORT=5000
CMD ["python", "-u", "-X", "gc_threshold=1000000", "v146.py"]
