# Dockerfile for running JaxMusic Telegram bot
FROM python:3.11-slim

# Install ffmpeg and other small deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot
COPY bot.py .

# Runtime env: TELEGRAM_TOKEN must be provided via env or docker run -e
ENV PYTHONUNBUFFERED=1

CMD ["python", "bot.py"]
