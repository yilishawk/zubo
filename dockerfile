FROM python:3.11-alpine

WORKDIR /app

RUN apk add --no-cache \
    ffmpeg \
    gcc \
    python3-dev \
    musl-dev \
    linux-headers && \
    rm -rf /var/cache/apk/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

RUN apk del gcc python3-dev musl-dev linux-headers

COPY v132.py .

ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["python", "v132.py"]
