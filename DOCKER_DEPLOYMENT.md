# Docker Deployment Guide

This guide explains how to deploy the Jenkins AI Chatbot using Docker and Docker Compose.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Architecture Overview](#architecture-overview)
- [Configuration](#configuration)
- [Advanced Deployment](#advanced-deployment)
- [Troubleshooting](#troubleshooting)
- [Production Considerations](#production-considerations)

## Prerequisites

- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher
- **System Requirements**:
  - Minimum 8GB RAM (16GB recommended for llama.cpp models)
  - 20GB free disk space
  - Multi-core CPU (GPU optional but recommended for faster inference)

## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/jenkinsci/resources-ai-chatbot-plugin.git
cd resources-ai-chatbot-plugin
```

### 2. Prepare the Models
Download the llama.cpp model and place it in the correct directory:

```bash
# Create models directory if it doesn't exist
mkdir -p chatbot-core/api/models/mistral

# Download the model (example using wget)
cd chatbot-core/api/models/mistral
wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf

# Or use any other Q4_K_M or similar quantized model
# Make sure the path in config.yml matches the actual model location
```

### 3. Build and Start Services
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

### 4. Access the Application
- **Frontend**: http://localhost
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### 5. Stop Services
```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v
```

## Architecture Overview

The Docker deployment consists of the following services:

```
┌─────────────────────────────────────────────────────────┐
│                      Internet/User                       │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ Port 80
                       ▼
┌──────────────────────────────────────────────────────────┐
│              Frontend (Nginx + React)                    │
│  - Serves static frontend assets                        │
│  - Proxies API requests to backend                      │
│  - Handles routing                                       │
└──────────────────┬───────────────────────────────────────┘
                   │
                   │ /api/* → backend:8000
                   ▼
┌──────────────────────────────────────────────────────────┐
│              Backend (FastAPI + llama.cpp)               │
│  - Handles chat requests                                 │
│  - Manages sessions                                      │
│  - Performs RAG with FAISS/Qdrant                        │
│  - Runs llama.cpp inference                              │
└──────────────────┬───────────────────────────────────────┘
                   │
                   │ Optional
                   ▼
┌──────────────────────────────────────────────────────────┐
│              Qdrant (Vector Database)                    │
│  - Alternative to FAISS for production                   │
│  - Scalable vector search                                │
│  - Persistent storage                                    │
└──────────────────────────────────────────────────────────┘
```

## Configuration

### Environment Variables

Create a `.env` file in the root directory:

```bash
# Backend Configuration
BACKEND_PORT=8000
BACKEND_WORKERS=1

# Frontend Configuration
FRONTEND_PORT=80

# Model Configuration
MODEL_PATH=/app/api/models/mistral/mistral-7b-instruct-v0.2.Q4_K_M.gguf
GPU_LAYERS=0  # Set to >0 if using GPU

# Vector Store (choose one)
VECTOR_STORE=faiss  # or 'qdrant'
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# Session Management
SESSION_TIMEOUT_HOURS=24
CLEANUP_INTERVAL_SECONDS=3600
```

### Volume Mounts

The following volumes are mounted for data persistence:

- **Models**: `./chatbot-core/api/models` → `/app/api/models` (read-only)
- **Data**: `./chatbot-core/data` → `/app/data` (embeddings, FAISS index)
- **Config**: `./chatbot-core/api/config/config.yml` → `/app/api/config/config.yml`

### Customizing Configuration

Edit `chatbot-core/api/config/config.yml` to customize:

```yaml
llm:
  model_path: "api/models/mistral/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
  max_tokens: 512
  context_length: 2048
  threads: 8
  gpu_layers: 0  # Increase for GPU acceleration

retrieval:
  embedding_model_name: "sentence-transformers/all-MiniLM-L6-v2"
  top_k: 3
```

## Advanced Deployment

### Using Qdrant Vector Database

For production deployments, Qdrant provides better scalability:

```bash
# Start services with Qdrant
docker-compose --profile qdrant up -d

# Or explicitly specify services
docker-compose up -d backend frontend qdrant
```

Update backend environment variables:
```yaml
environment:
  - VECTOR_STORE=qdrant
  - QDRANT_HOST=qdrant
  - QDRANT_PORT=6333
```

### GPU Acceleration

To enable GPU acceleration with llama.cpp:

1. **Install NVIDIA Container Toolkit**:
```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

2. **Update docker-compose.yml** for backend service:
```yaml
backend:
  build:
    context: ./chatbot-core
    dockerfile: Dockerfile
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
  environment:
    - GPU_LAYERS=35  # Adjust based on your GPU VRAM
```

3. **Rebuild with GPU support**:
```bash
# Edit chatbot-core/Dockerfile and uncomment llama-cpp-python installation with GPU flags
docker-compose build --no-cache backend
docker-compose up -d
```

### Scaling

To scale the backend for higher load:

```bash
# Scale backend to 3 instances
docker-compose up -d --scale backend=3

# Add load balancer (requires nginx configuration update)
```

For production, consider using:
- **Kubernetes** for orchestration
- **Horizontal Pod Autoscaling** for automatic scaling
- **Persistent volumes** for model and data storage

### Using Redis for Session Management

Enable Redis for distributed session storage:

```bash
# Start services with Redis
docker-compose --profile redis up -d backend frontend redis
```

Update backend code to use Redis sessions (requires code modification).

## Troubleshooting

### Common Issues

#### 1. Backend Health Check Failing
```bash
# Check backend logs
docker-compose logs backend

# Common causes:
# - Model file not found
# - Insufficient memory
# - Port conflict
```

#### 2. Model Loading Issues
```bash
# Verify model path
docker-compose exec backend ls -lh /app/api/models/mistral/

# Check model path in config
docker-compose exec backend cat /app/api/config/config.yml | grep model_path
```

#### 3. Out of Memory
```bash
# Reduce model size or use smaller quantization
# Q4_K_M → Q4_K_S or Q3_K_M

# Increase Docker memory limit
# Docker Desktop: Settings → Resources → Memory
```

#### 4. Frontend Can't Connect to Backend
```bash
# Check network
docker network inspect chatbot-network

# Check backend is running
docker-compose ps backend

# Test API directly
curl http://localhost:8000/api/chatbot/health
```

### Logs and Debugging

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Enter container shell
docker-compose exec backend bash
docker-compose exec frontend sh

# Check resource usage
docker stats
```

## Production Considerations

### Security

1. **Use HTTPS**: Deploy behind a reverse proxy with SSL/TLS
   ```bash
   # Example with Traefik or Caddy
   ```

2. **Update CORS settings**: Restrict allowed origins
   ```yaml
   cors:
     allowed_origins:
       - "https://yourdomain.com"
   ```

3. **Use secrets management**: Don't commit sensitive data
   ```bash
   # Use Docker secrets or environment variables
   docker-compose --env-file .env.production up -d
   ```

4. **Non-root containers**: Already implemented in Dockerfiles

### Performance Optimization

1. **Use production WSGI server**: Already using uvicorn with workers
2. **Enable caching**: Add Redis for session and response caching
3. **Optimize model**: Use appropriate quantization for your hardware
4. **CDN for static assets**: Serve frontend assets via CDN

### Monitoring

Set up monitoring with:
- **Prometheus** for metrics collection
- **Grafana** for visualization
- **Loki** for log aggregation

Example prometheus config:
```yaml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
```

### Backup and Recovery

```bash
# Backup volumes
docker run --rm \
  -v chatbot_qdrant_storage:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/qdrant-backup.tar.gz /data

# Restore volumes
docker run --rm \
  -v chatbot_qdrant_storage:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/qdrant-backup.tar.gz -C /
```

### Health Monitoring

All services include health checks:
```bash
# Check health status
docker-compose ps

# Restart unhealthy services automatically
docker-compose up -d --force-recreate
```

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [llama.cpp Documentation](https://github.com/ggerganov/llama.cpp)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)

## Support

For issues and questions:
- GitHub Issues: https://github.com/jenkinsci/resources-ai-chatbot-plugin/issues
- Jenkins Community: https://community.jenkins.io/

---

**Happy Deploying! 🚀**
