FROM python:3.9-slim

WORKDIR /app

# Cài đặt dependencies hệ thống
RUN apt-get update && apt-get install -y \
    build-essential \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Xoá redis cũ và cài mới, tránh Docker cache giữ lại
RUN pip install --upgrade pip \
    && pip uninstall -y redis || true \
    && rm -rf /usr/local/lib/python3.9/site-packages/redis \
    && rm -rf /usr/local/lib/python3.9/site-packages/redis-*.dist-info \
    && pip install --no-cache-dir redis==7.0.1 \
    && pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ source code
COPY . .

ENV PYTHONPATH=/app

EXPOSE 8082

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8082"]
