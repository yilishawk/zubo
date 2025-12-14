FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir aiohttp flask

COPY v101.py .

EXPOSE 5000

CMD ["python", "v101.py"]