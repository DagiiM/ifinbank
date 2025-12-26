# ===============================================================================
# iFin Bank Verification System - Provisioning
# ===============================================================================

This directory contains all deployment and infrastructure configuration for the
iFin Bank Verification System.

## 📁 Directory Structure

```
provisioning/
├── docker/                     # Docker build files
│   ├── Dockerfile             # Production multi-stage build
│   └── Dockerfile.dev         # Development build
│
├── nginx/                      # Nginx configuration
│   ├── nginx.conf             # Main nginx config
│   ├── conf.d/
│   │   └── ifinbank.conf      # Server configuration
│   └── ssl/                   # SSL certificates (not in git)
│       ├── fullchain.pem
│       └── privkey.pem
│
├── postgres/                   # PostgreSQL initialization
│   └── init.sql               # Database extensions setup
│
├── scripts/                    # Deployment scripts
│   ├── deploy.sh              # Production deployment
│   ├── backup.sh              # Database backup
│   └── ssl-generate.sh        # Generate self-signed SSL
│
├── docker-compose.yml         # Production stack
├── docker-compose.dev.yml     # Development stack
├── requirements-prod.txt      # Production Python dependencies
├── .env.production.example    # Environment template
└── README.md                  # This file
```

---

## 🚀 Quick Start

### Development Environment

```bash
cd provisioning

# Start development stack
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Stop
docker-compose -f docker-compose.dev.yml down
```

### Production Environment

```bash
cd provisioning

# 1. Configure environment
cp .env.production.example .env.production
nano .env.production  # Edit with your values

# 2. Generate SSL certificates (or add your own)
./scripts/ssl-generate.sh

# 3. Deploy
./scripts/deploy.sh
```

---

## 🐳 Docker Services

### Production Stack (`docker-compose.yml`)

| Service | Image | Port | Description |
|---------|-------|------|-------------|
| **web** | Custom | 8000 (internal) | Django + Gunicorn |
| **celery_worker** | Custom | - | Background tasks |
| **celery_beat** | Custom | - | Scheduled tasks |
| **nginx** | nginx:alpine | 80, 443 | Reverse proxy |
| **db** | postgres:15-alpine | 5432 (internal) | PostgreSQL database |
| **redis** | redis:7-alpine | 6379 (internal) | Cache & message broker |
| **vllm** | vllm/vllm-openai | 8000 (internal) | DeepSeek-OCR AI |
| **chromadb** | chromadb/chroma | 8000 (internal) | Vector database |

### Development Stack (`docker-compose.dev.yml`)

| Service | Port | Description |
|---------|------|-------------|
| **web** | 8000 | Django dev server |
| **db** | 5432 | PostgreSQL |
| **redis** | 6379 | Redis |
| **chromadb** | 8001 | ChromaDB |

---

## ⚙️ Configuration

### Environment Variables

Copy `.env.production.example` to `.env.production` and configure:

```env
# Required
SECRET_KEY=<generate-secure-key>
POSTGRES_PASSWORD=<strong-password>
ALLOWED_HOSTS=your-domain.com

# Optional
USE_VLLM_OCR=true
USE_CHROMADB=true
```

### SSL Certificates

Place SSL certificates in `nginx/ssl/`:
- `fullchain.pem` - Certificate chain
- `privkey.pem` - Private key

For development, generate self-signed:
```bash
./scripts/ssl-generate.sh
```

For production, use Let's Encrypt or your CA.

---

## 🔧 Common Commands

### Start/Stop Services

```bash
# Production
docker-compose up -d
docker-compose down

# Development
docker-compose -f docker-compose.dev.yml up -d
docker-compose -f docker-compose.dev.yml down
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f vllm
```

### Execute Commands

```bash
# Django shell
docker-compose exec web python manage.py shell

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Seed policies
docker-compose exec web python manage.py seed_policies
```

### Backup

```bash
# Database backup
./scripts/backup.sh
```

---

## 🔒 Security Checklist

- [ ] Generate unique `SECRET_KEY`
- [ ] Set strong `POSTGRES_PASSWORD`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Add valid SSL certificates
- [ ] Configure firewall (only 80/443)
- [ ] Enable database backups
- [ ] Set up monitoring
- [ ] Review Django security settings

---

## 📊 Monitoring

### Health Endpoints

| Endpoint | Description |
|----------|-------------|
| `/health/` | Overall health check |
| `/health/ready/` | Readiness probe |
| `/health/live/` | Liveness probe |

### Service Health

```bash
# Check all services
docker-compose ps

# Container stats
docker stats

# GPU monitoring (vLLM)
nvidia-smi
```

---

## 🛠️ Troubleshooting

### vLLM Not Starting

```bash
# Check GPU availability
docker run --rm --gpus all nvidia/cuda:12.1-base nvidia-smi

# Check vLLM logs
docker-compose logs vllm
```

### Database Connection Issues

```bash
# Check database health
docker-compose exec db pg_isready -U ifinbank

# Check logs
docker-compose logs db
```

### Permission Issues

```bash
# Fix volume permissions
docker-compose exec web chown -R appuser:appgroup /app/media
```

---

## 📚 Additional Resources

- [DEPLOYMENT.md](../docs/DEPLOYMENT.md) - Full deployment guide
- [VLLM_SETUP.md](../docs/VLLM_SETUP.md) - vLLM configuration
- [README.md](../README.md) - Project overview
