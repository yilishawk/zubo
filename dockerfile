FROM python:3.10-slim-bullseye

WORKDIR /app

# 替换阿里云源，安装ffmpeg等依赖（保留你的配置）
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

# 配置pip国内源（保留你的配置）
RUN pip install --upgrade pip setuptools wheel -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    mkdir -p ~/.pip && \
    echo "[global]" > ~/.pip/pip.conf && \
    echo "index-url = https://pypi.tuna.tsinghua.edu.cn/simple" >> ~/.pip/pip.conf && \
    echo "extra-index-url = https://mirrors.aliyun.com/pypi/simple/ https://pypi.org/simple/" >> ~/.pip/pip.conf && \
    echo "trusted-host = pypi.tuna.tsinghua.edu.cn mirrors.aliyun.com pypi.org files.pythonhosted.org" >> ~/.pip/pip.conf

# 复制依赖清单并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 创建配置和输出目录（确保权限）
RUN mkdir -p /app/config /app/output && \
    chmod 777 /app/config /app/output && \
    chown -R root:root /app

# 复制你的代码（v146.py）和前端静态文件目录
COPY v146.py .
COPY static /app/static

# 暴露端口
EXPOSE 5000
ENV PORT=5000

# 最终正确的启动命令（兼容Python GC参数 + gunicorn异步模式）
CMD ["python", "-u", "-X", "gc_threshold=1000000", "-m", "gunicorn", "-w", "4", "-k", "gevent", "-b", "0.0.0.0:5000", "v146:app"]