# ===============================================================================
# iFin Bank Verification System - Production Deployment Guide
# ===============================================================================

## Overview

This guide covers deploying the iFin Bank Verification System to production
with Docker, including the vLLM/DeepSeek-OCR AI service.

---

## Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Docker | 24.0+ | Latest |
| Docker Compose | 2.20+ | Latest |
| NVIDIA GPU | RTX 3090 (24GB) | A100 (40GB+) |
| NVIDIA Driver | 525+ | 535+ |
| nvidia-docker | 2.0+ | Latest |
| RAM | 32GB | 64GB+ |
| Storage | 100GB SSD | 500GB NVMe |

---

## Quick Deploy

### 1. Clone Repository

```bash
git clone <repository-url>
cd ifinbank
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.production.example .env.production

# Edit with your values
nano .env.production
```

**Required settings:**
- `SECRET_KEY` - Generate a secure key
- `POSTGRES_PASSWORD` - Strong database password
- `ALLOWED_HOSTS` - Your domain names

### 3. SSL Certificates

Place your SSL certificates in `docker/nginx/ssl/`:
- `fullchain.pem` - Full certificate chain
- `privkey.pem` - Private key

For development/testing, generate self-signed:
```bash
mkdir -p docker/nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout docker/nginx/ssl/privkey.pem \
    -out docker/nginx/ssl/fullchain.pem
```

### 4. Deploy Stack

```bash
# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 5. Initialize Application

```bash
# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Seed policies
docker-compose exec web python manage.py seed_policies

# Sync to ChromaDB
docker-compose exec web python manage.py sync_policies
```

---

## Service Architecture

```
                    ┌─────────────────┐
                    │     Nginx       │
                    │   (Port 80/443) │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ Static   │  │  Django  │  │  Media   │
        │ Files    │  │   App    │  │  Files   │
        └──────────┘  └────┬─────┘  └──────────┘
                           │
     ┌─────────────────────┼─────────────────────┐
     │                     │                     │
     ▼                     ▼                     ▼
┌──────────┐        ┌──────────┐          ┌──────────┐
│PostgreSQL│        │  Redis   │          │  Celery  │
│   (DB)   │        │ (Cache)  │          │ (Tasks)  │
└──────────┘        └──────────┘          └──────────┘
                                                │
                    ┌───────────────────────────┤
                    │                           │
                    ▼                           ▼
             ┌──────────┐               ┌──────────┐
             │  vLLM    │               │ ChromaDB │
             │DeepSeek  │               │(Vectors) │
             └──────────┘               └──────────┘
```

---

## GPU Configuration

### NVIDIA Docker Setup

```bash
# Install nvidia-docker2
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
    sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

### Verify GPU Access

```bash
docker run --rm --gpus all nvidia/cuda:12.1-base nvidia-smi
```

### vLLM Model Download

The DeepSeek-OCR model (~7GB) downloads automatically on first start.
For faster deployment, pre-download:

```bash
# Pre-download model
docker-compose run --rm vllm huggingface-cli download deepseek-ai/DeepSeek-OCR
```

---

## Scaling

### Horizontal Scaling (Web Workers)

```yaml
# In docker-compose.yml
web:
  deploy:
    replicas: 4
```

### vLLM Multi-GPU

```yaml
vllm:
  command: >
    --model deepseek-ai/DeepSeek-OCR
    --tensor-parallel-size 2  # Use 2 GPUs
    --trust-remote-code
```

---

## Monitoring

### Health Checks

| Service | Endpoint | Expected |
|---------|----------|----------|
| Django | `/health/` | HTTP 200 |
| vLLM | `/health` | `{"status":"healthy"}` |
| ChromaDB | `/api/v1/heartbeat` | HTTP 200 |

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f vllm
```

### Resource Monitoring

```bash
# Container stats
docker stats

# GPU monitoring
nvidia-smi -l 1
```

---

## Backup & Recovery

### Database Backup

```bash
# Backup
docker-compose exec db pg_dump -U ifinbank ifinbank > backup.sql

# Restore
cat backup.sql | docker-compose exec -T db psql -U ifinbank ifinbank
```

### Volume Backup

```bash
# Backup all volumes
docker run --rm \
    -v ifinbank_postgres_data:/data \
    -v $(pwd)/backups:/backup \
    alpine tar czf /backup/postgres_$(date +%Y%m%d).tar.gz /data
```

---

## Troubleshooting

### vLLM Won't Start

```bash
# Check GPU memory
nvidia-smi

# Reduce memory usage
# In docker-compose.yml:
command: >
  --model deepseek-ai/DeepSeek-OCR
  --gpu-memory-utilization 0.7  # Reduce from 0.9
```

### Connection Refused

```bash
# Check if services are running
docker-compose ps

# Check network
docker network ls
docker network inspect ifinbank_ifinbank_network
```

### Database Connection Failed

```bash
# Check database health
docker-compose exec db pg_isready -U ifinbank

# Check logs
docker-compose logs db
```

---

## Security Checklist

- [ ] Change default `SECRET_KEY`
- [ ] Set strong `POSTGRES_PASSWORD`
- [ ] Configure `ALLOWED_HOSTS` properly
- [ ] Enable SSL with valid certificates
- [ ] Configure firewall (only 80/443 exposed)
- [ ] Set up fail2ban for brute force protection
- [ ] Enable database backups
- [ ] Configure log rotation
- [ ] Set up monitoring alerts
- [ ] Review Django security settings

---

## Maintenance

### Updates

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose build web
docker-compose up -d web

# Run migrations
docker-compose exec web python manage.py migrate
```

### Cleanup

```bash
# Remove unused images
docker image prune -a

# Remove unused volumes (CAREFUL!)
docker volume prune
```

---

## Support

- GitHub Issues: <repository-issues-url>
- Documentation: See `docs/` directory
- Email: support@ifinbank.com
