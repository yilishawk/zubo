FROM jrottenberg/ffmpeg:6.0-slim AS ffmpeg-build

FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir aiohttp flask

COPY v101.py .

COPY --from=ffmpeg-build /usr/local/bin/ffmpeg /usr/local/bin/ffmpeg
COPY --from=ffmpeg-build /usr/local/bin/ffprobe /usr/local/bin/ffprobe

EXPOSE 5000

CMD ["python", "v101.py"]
