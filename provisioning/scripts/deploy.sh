#!/bin/bash

#===============================================================================
# iFin Bank - Production Deployment Script
#===============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROVISIONING_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║         iFin Bank - Production Deployment                     ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

cd "$PROVISIONING_DIR"

# Check prerequisites
echo -e "${CYAN}[1/6] Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker not found. Please install Docker.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Docker Compose not found. Please install Docker Compose.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker and Docker Compose found${NC}"

# Check environment file
echo -e "${CYAN}[2/6] Checking configuration...${NC}"

if [ ! -f ".env.production" ]; then
    echo -e "${YELLOW}Warning: .env.production not found${NC}"
    if [ -f ".env.production.example" ]; then
        echo "Creating from example..."
        cp .env.production.example .env.production
        echo -e "${YELLOW}Please edit .env.production with your settings${NC}"
        read -p "Press Enter to continue after editing, or Ctrl+C to abort..."
    else
        echo -e "${RED}No environment template found. Aborting.${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✓ Environment configured${NC}"

# Check SSL certificates
echo -e "${CYAN}[3/6] Checking SSL certificates...${NC}"

if [ ! -f "nginx/ssl/fullchain.pem" ] || [ ! -f "nginx/ssl/privkey.pem" ]; then
    echo -e "${YELLOW}Warning: SSL certificates not found${NC}"
    read -p "Generate self-signed certificates? (y/N): " gen_ssl
    if [[ $gen_ssl =~ ^[Yy]$ ]]; then
        ./scripts/ssl-generate.sh
    else
        echo -e "${YELLOW}Continuing without SSL (not recommended for production)${NC}"
    fi
else
    echo -e "${GREEN}✓ SSL certificates found${NC}"
fi

# Build images
echo -e "${CYAN}[4/6] Building Docker images...${NC}"

docker-compose build --no-cache

echo -e "${GREEN}✓ Images built${NC}"

# Start services
echo -e "${CYAN}[5/6] Starting services...${NC}"

docker-compose up -d

echo -e "${GREEN}✓ Services started${NC}"

# Wait for services
echo -e "${CYAN}[6/6] Waiting for services to be healthy...${NC}"

echo "Waiting for database..."
sleep 10

# Initialize application
echo -e "${CYAN}Initializing application...${NC}"

docker-compose exec -T web python manage.py migrate --no-input
docker-compose exec -T web python manage.py collectstatic --no-input

# Check if superuser exists
HAS_SUPERUSER=$(docker-compose exec -T web python -c "
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings_production'
import django
django.setup()
from apps.accounts.models import User
print('yes' if User.objects.filter(is_superuser=True).exists() else 'no')
" 2>/dev/null || echo "no")

if [ "$HAS_SUPERUSER" = "no" ]; then
    echo -e "${YELLOW}No superuser found. Creating one...${NC}"
    docker-compose exec web python manage.py createsuperuser
fi

# Seed policies
docker-compose exec -T web python manage.py seed_policies 2>/dev/null || true

# Health check
echo -e "${CYAN}Checking service health...${NC}"
sleep 5

if curl -sf http://localhost/health/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Application is healthy${NC}"
else
    echo -e "${YELLOW}Warning: Health check failed (may still be starting)${NC}"
fi

# Summary
echo ""
echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                  Deployment Complete! 🎉                      ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${CYAN}Service Status:${NC}"
docker-compose ps

echo ""
echo -e "${CYAN}Access:${NC}"
echo "  Application: https://localhost"
echo "  Health:      https://localhost/health/"
echo ""
echo -e "${CYAN}Commands:${NC}"
echo "  Logs:    docker-compose logs -f"
echo "  Stop:    docker-compose down"
echo "  Restart: docker-compose restart"
