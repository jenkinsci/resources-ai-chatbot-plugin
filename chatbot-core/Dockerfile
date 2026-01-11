# Multi-stage Dockerfile for FastAPI backend with llama.cpp support
FROM python:3.11-slim as builder

# Install build dependencies for llama-cpp-python
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    wget \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Optionally build llama-cpp-python with CPU support
# Uncomment the following lines if you want to include llama-cpp-python
# RUN CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS" \
#     pip install --no-cache-dir --user llama-cpp-python==0.3.9

# =========================
# Final Stage
# =========================
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libopenblas0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 chatbot && \
    mkdir -p /app /app/data /app/api/models && \
    chown -R chatbot:chatbot /app

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /home/chatbot/.local

# Copy application code
COPY --chown=chatbot:chatbot . .

# Set environment variables
ENV PATH=/home/chatbot/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Switch to non-root user
USER chatbot

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/chatbot/health || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
