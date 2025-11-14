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

# Upgrade pip
RUN pip install --upgrade pip

# Xoá redis + aiocache cũ nếu có
RUN pip uninstall -y redis aiocache || true
RUN rm -rf /usr/local/lib/python3.9/site-packages/redis*
RUN rm -rf /usr/local/lib/python3.9/site-packages/aiocache*

# Cài redis + aiocache trước
RUN pip install --no-cache-dir redis==7.0.1 aiocache==0.11.1

# Cài các package còn lại
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

ENV PYTHONPATH=/app
EXPOSE 8082

# Kiểm tra version redis + aiocache
RUN python - <<EOF
import redis, aiocache
print('redis.version=', redis.__version__, 'file=', redis.__file__)
print('aiocache.version=', aiocache.__version__, 'file=', aiocache.__file__)
EOF

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8082"]
