FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .
COPY telegram_bot.py .
COPY launcher.py .

CMD ["python", "launcher.py"]
