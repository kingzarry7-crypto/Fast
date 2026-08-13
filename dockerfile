FROM python:3.12-slim

# Prevent Python from buffering stdout/stderr (ensures real-time docker logs)
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (takes advantage of Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application code into the container
COPY . .

CMD ["python", "launcher.py"]
