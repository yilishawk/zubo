FROM python:3.11-alpine

WORKDIR /app

COPY requirements.txt .

RUN apk add --no-cache ffmpeg && \
    rm -rf /var/cache/apk/*

RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY v132.py .

ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["python", "v132.py"]
