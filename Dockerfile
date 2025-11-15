# -----------------------------
# Dockerfile cho FastAPI / Alpha Backend
# -----------------------------
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Cài các dependencies hệ thống
RUN apt-get update && apt-get install -y \
    build-essential \
    ffmpeg \
    libsndfile1 \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Cài pip packages triệt để, ép cài lại toàn bộ, xóa cache
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --force-reinstall -r requirements.txt \
    && pip install --no-cache-dir --force-reinstall "redis==6.4.0" "aiocache==0.12.3" \
    && rm -rf /root/.cache/pip

# Copy toàn bộ code
COPY . .

# Thiết lập PYTHONPATH
ENV PYTHONPATH=/app

# Expose port FastAPI
EXPOSE 8082

# Command để chạy ứng dụng
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8082", "--reload"]
