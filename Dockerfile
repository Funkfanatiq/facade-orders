# Flask + LibreOffice для ТОРГ-12 (Excel → PDF)
FROM python:3.11-slim-bookworm

# LibreOffice для конвертации xlsx → pdf
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p uploads

ENV PORT=10000
EXPOSE 10000

# Render передаёт PORT через env. Таймаут 300 с — иначе загрузка нескольких крупных PDF обрывается (~30 с по умолчанию).
# При необходимости: GUNICORN_TIMEOUT=600 в Environment на Render.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --timeout ${GUNICORN_TIMEOUT:-300} --graceful-timeout 120 app:app"]
