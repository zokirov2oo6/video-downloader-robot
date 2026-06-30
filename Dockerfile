FROM python:3.11-slim

# ffmpeg yt-dlp uchun shart: MP3 audio ajratib olish va video/audio
# oqimlarini birlashtirish (merge) shu orqali ishlaydi.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

CMD ["python3", "bot.py"]
