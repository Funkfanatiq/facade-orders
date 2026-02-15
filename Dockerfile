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

# Render передаёт PORT через env при запуске
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} app:app"]
