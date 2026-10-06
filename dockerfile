FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TZ=UTC
ENV PLAYWRIGHT_BROWSERS_PATH=/app/.playwright

WORKDIR /app

# System dependencies required by the API, media stack, and Chromium.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    chromium \
    libnss3 \
    libnspr4 \
    libgbm1 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libasound2 \
    libpangocairo-1.0-0 \
    libxss1 \
    libgtk-3-0 \
    libxshmfence1 \
    libglu1 \
    libffi-dev \
    libopus-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN adduser --disabled-password --gecos "" appuser

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/.playwright && \
    PLAYWRIGHT_BROWSERS_PATH=/app/.playwright python -m playwright install chromium

COPY . .

RUN mkdir -p /app/data && \
    chown -R appuser:appuser /app

RUN echo "=== BROWSER BUILD CHECK ===" && \
    command -v chromium && \
    ls -l /usr/bin/chromium && \
    PLAYWRIGHT_BROWSERS_PATH=/app/.playwright python -c "import shutil; from pathlib import Path; from playwright.sync_api import sync_playwright; p=shutil.which('chromium'); print('SYSTEM_CHROMIUM='+str(p)); assert p; pw=sync_playwright().start(); print('PLAYWRIGHT_CHROMIUM='+str(Path(pw.chromium.executable_path))); pw.stop()"

RUN chmod +x /app/start.sh

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -fsS http://localhost:$${PORT:-8000}/health || exit 1

CMD ["./start.sh"]