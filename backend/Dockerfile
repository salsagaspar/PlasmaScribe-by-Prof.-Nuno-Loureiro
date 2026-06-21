FROM python:3.10-slim

WORKDIR /app

# Install system dependencies needed for compiling ChromaDB/scipy if necessary
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
# Optimize PyTorch: install CPU-only version first to prevent 1.5GB of CUDA library downloads
RUN pip install --no-cache-dir torch==2.12.1 --extra-index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
