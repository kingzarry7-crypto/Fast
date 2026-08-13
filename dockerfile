# Use a specific slim image
FROM python:3.12-slim

# Prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1
# Prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system dependencies
# ffmpeg is required for the discord.py voice features
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
RUN adduser --disabled-password --gecos "" appuser

# Install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Change ownership of the app directory to the new user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Start the application
CMD ["python", "launcher.py"]
