FROM python:3.10-slim-bullseye

WORKDIR /app

# 关键修复：替换为阿里云Debian源（兼容Bullseye，无403）
# 先清空原有源列表，重新写入阿里云源（避免源路径错误）
RUN echo "deb http://mirrors.aliyun.com/debian/ bullseye main contrib non-free" > /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian/ bullseye-updates main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security/ bullseye-security main contrib non-free" >> /etc/apt/sources.list

# 安装依赖（保留你原有的包，精简且无冗余）
RUN apt update && apt install -y --no-install-recommends \
    ffmpeg \
    libc6-dev \
    gcc \
    procps \
    vim \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖（保留清华PyPI源，加速安装）
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 保留你原有的目录权限配置
RUN mkdir -p /app/config && chmod 777 /app/config && chown -R root:root /app

# 保留你原有的文件复制逻辑
COPY v146.py .
COPY static /app/static

# 保留端口和环境变量配置
EXPOSE 5000
ENV PORT=5000

# 保留你原有的启动命令（-u 无缓冲输出，gc_threshold 优化GC）
CMD ["python", "-u", "-X", "gc_threshold=1000000", "v146.py"]
