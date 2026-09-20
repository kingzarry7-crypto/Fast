FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TZ=UTC

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libffi-dev \
    libopus-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN adduser --disabled-password --gecos "" appuser

# Install Python dependencies
COPY requirements.txt .

RUN python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Persistent data directory
RUN mkdir -p /app/data && \
    chown -R appuser:appuser /app

# Make start.sh executable (safe even if not present yet)
RUN chmod +x /app/start.sh 2>/dev/null || true

USER appuser

# Railway supplies PORT when needed
EXPOSE 8000

# Healthcheck so Railway knows the API is up
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -fsS http://localhost:${PORT:-8000}/health || exit 1

# Start API + bots together
CMD ["./start.sh"]
