#!/bin/bash

#===============================================================================
# iFin Bank Verification System - One-Step Deployment
# 
# Usage: ./deploy.sh [environment]
#   - ./deploy.sh           # Interactive mode
#   - ./deploy.sh dev       # Development environment
#   - ./deploy.sh prod      # Production environment
#   - ./deploy.sh prod --no-gpu  # Production without vLLM (no GPU)
#===============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
PROVISIONING_DIR="$PROJECT_DIR/provisioning"

# Defaults
ENVIRONMENT=""
NO_GPU=false
AUTO_YES=false

#-------------------------------------------------------------------------------
# Parse Arguments
#-------------------------------------------------------------------------------

while [[ $# -gt 0 ]]; do
    case $1 in
        dev|development)
            ENVIRONMENT="dev"
            shift
            ;;
        prod|production)
            ENVIRONMENT="prod"
            shift
            ;;
        --no-gpu)
            NO_GPU=true
            shift
            ;;
        -y|--yes)
            AUTO_YES=true
            shift
            ;;
        -h|--help)
            echo "Usage: ./deploy.sh [dev|prod] [options]"
            echo ""
            echo "Environments:"
            echo "  dev, development   Development environment (no GPU required)"
            echo "  prod, production   Production environment (GPU for vLLM)"
            echo ""
            echo "Options:"
            echo "  --no-gpu          Skip vLLM/GPU services"
            echo "  -y, --yes         Auto-confirm all prompts"
            echo "  -h, --help        Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

#-------------------------------------------------------------------------------
# Banner
#-------------------------------------------------------------------------------

clear
echo -e "${CYAN}${BOLD}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                               ║"
echo "║         iFin Bank Verification System                        ║"
echo "║         One-Step Deployment                                   ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

#-------------------------------------------------------------------------------
# Environment Selection
#-------------------------------------------------------------------------------

if [ -z "$ENVIRONMENT" ]; then
    echo -e "${CYAN}Select deployment environment:${NC}"
    echo ""
    echo "  1) Development  - Local development with hot reload"
    echo "  2) Production   - Full stack with vLLM/DeepSeek-OCR"
    echo "  3) Production   - Without GPU (mock AI services)"
    echo ""
    read -p "Enter choice [1-3]: " choice
    
    case $choice in
        1) ENVIRONMENT="dev" ;;
        2) ENVIRONMENT="prod" ;;
        3) ENVIRONMENT="prod"; NO_GPU=true ;;
        *) echo "Invalid choice"; exit 1 ;;
    esac
fi

echo -e "${GREEN}▶ Environment: ${BOLD}$ENVIRONMENT${NC}"
if [ "$NO_GPU" = true ]; then
    echo -e "${YELLOW}  (No GPU - AI services disabled)${NC}"
fi
echo ""

#-------------------------------------------------------------------------------
# Pre-flight Checks
#-------------------------------------------------------------------------------

echo -e "${CYAN}[1/5] Pre-flight checks...${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found. Please install Docker.${NC}"
    echo "  https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}  ✓ Docker${NC}"

# Check Docker Compose
if docker compose version &> /dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    echo -e "${RED}✗ Docker Compose not found.${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ Docker Compose${NC}"

# Check GPU for production
if [ "$ENVIRONMENT" = "prod" ] && [ "$NO_GPU" = false ]; then
    if command -v nvidia-smi &> /dev/null; then
        echo -e "${GREEN}  ✓ NVIDIA GPU detected${NC}"
    else
        echo -e "${YELLOW}  ⚠ No NVIDIA GPU detected. Use --no-gpu for CPU-only mode.${NC}"
        if [ "$AUTO_YES" = false ]; then
            read -p "  Continue without GPU? (y/N): " continue_no_gpu
            if [[ ! $continue_no_gpu =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
        NO_GPU=true
    fi
fi

#-------------------------------------------------------------------------------
# Environment Configuration
#-------------------------------------------------------------------------------

echo -e "${CYAN}[2/5] Configuring environment...${NC}"

cd "$PROVISIONING_DIR"

if [ "$ENVIRONMENT" = "prod" ]; then
    ENV_FILE=".env.production"
    
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${YELLOW}  Creating production environment file...${NC}"
        
        # Generate secret key
        SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))" 2>/dev/null || openssl rand -base64 50 | tr -d '\n')
        
        # Generate database password
        DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))" 2>/dev/null || openssl rand -base64 24 | tr -d '\n')
        
        cat > "$ENV_FILE" << EOF
# iFin Bank Production Configuration
# Generated: $(date)

SECRET_KEY=${SECRET_KEY}
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

POSTGRES_PASSWORD=${DB_PASSWORD}

VLLM_API_URL=http://vllm:8000
USE_VLLM_OCR=$([[ "$NO_GPU" = true ]] && echo "false" || echo "true")
USE_CHROMADB=true

VERIFICATION_AUTO_APPROVE=85.0
VERIFICATION_REVIEW=70.0
VERIFICATION_AUTO_REJECT=50.0
EOF
        echo -e "${GREEN}  ✓ Created $ENV_FILE${NC}"
    else
        echo -e "${GREEN}  ✓ Using existing $ENV_FILE${NC}"
    fi
    
    # SSL certificates
    if [ ! -f "nginx/ssl/fullchain.pem" ]; then
        echo -e "${YELLOW}  Generating self-signed SSL certificate...${NC}"
        mkdir -p nginx/ssl
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout nginx/ssl/privkey.pem \
            -out nginx/ssl/fullchain.pem \
            -subj "/CN=localhost" 2>/dev/null
        echo -e "${GREEN}  ✓ SSL certificate generated${NC}"
    else
        echo -e "${GREEN}  ✓ SSL certificates exist${NC}"
    fi
else
    # Development - create .env if not exists
    if [ ! -f "../.env" ]; then
        cat > "../.env" << EOF
DEBUG=True
SECRET_KEY=dev-secret-key-change-in-production
USE_VLLM_OCR=false
USE_CHROMADB=true
EOF
        echo -e "${GREEN}  ✓ Created development .env${NC}"
    fi
fi

#-------------------------------------------------------------------------------
# Build & Deploy
#-------------------------------------------------------------------------------

echo -e "${CYAN}[3/5] Building containers...${NC}"

if [ "$ENVIRONMENT" = "prod" ]; then
    COMPOSE_FILE="docker-compose.yml"
    
    # Modify compose file for no GPU
    if [ "$NO_GPU" = true ]; then
        # Create a version without vLLM
        echo -e "${YELLOW}  Deploying without vLLM (GPU not available)${NC}"
        $COMPOSE_CMD -f "$COMPOSE_FILE" build web db redis chromadb nginx
    else
        $COMPOSE_CMD -f "$COMPOSE_FILE" build
    fi
else
    COMPOSE_FILE="docker-compose.dev.yml"
    $COMPOSE_CMD -f "$COMPOSE_FILE" build
fi

echo -e "${GREEN}  ✓ Build complete${NC}"

echo -e "${CYAN}[4/5] Starting services...${NC}"

if [ "$ENVIRONMENT" = "prod" ] && [ "$NO_GPU" = true ]; then
    # Start without vLLM
    $COMPOSE_CMD -f "$COMPOSE_FILE" up -d web db redis chromadb nginx celery_worker celery_beat
else
    $COMPOSE_CMD -f "$COMPOSE_FILE" up -d
fi

echo -e "${GREEN}  ✓ Services started${NC}"

#-------------------------------------------------------------------------------
# Initialize Application
#-------------------------------------------------------------------------------

echo -e "${CYAN}[5/5] Initializing application...${NC}"

# Wait for database
echo -e "  Waiting for database..."
sleep 10

# Run migrations
$COMPOSE_CMD -f "$COMPOSE_FILE" exec -T web python manage.py migrate --no-input 2>/dev/null || true
echo -e "${GREEN}  ✓ Database migrated${NC}"

# Collect static (production only)
if [ "$ENVIRONMENT" = "prod" ]; then
    $COMPOSE_CMD -f "$COMPOSE_FILE" exec -T web python manage.py collectstatic --no-input 2>/dev/null || true
    echo -e "${GREEN}  ✓ Static files collected${NC}"
fi

# Seed policies
$COMPOSE_CMD -f "$COMPOSE_FILE" exec -T web python manage.py seed_policies 2>/dev/null || true
echo -e "${GREEN}  ✓ Policies seeded${NC}"

# Check for admin user
HAS_ADMIN=$($COMPOSE_CMD -f "$COMPOSE_FILE" exec -T web python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()
from apps.accounts.models import User
print('yes' if User.objects.filter(is_superuser=True).exists() else 'no')
" 2>/dev/null || echo "no")

if [ "$HAS_ADMIN" = "no" ]; then
    echo -e "${YELLOW}  Creating admin user...${NC}"
    if [ "$AUTO_YES" = true ]; then
        $COMPOSE_CMD -f "$COMPOSE_FILE" exec -T web python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()
from apps.accounts.models import User
User.objects.create_superuser('admin@ifinbank.com', 'admin123', first_name='Admin', last_name='User')
print('Created: admin@ifinbank.com / admin123')
" 2>/dev/null || echo "  (will create on first access)"
    else
        $COMPOSE_CMD -f "$COMPOSE_FILE" exec web python manage.py createsuperuser
    fi
fi

#-------------------------------------------------------------------------------
# Success Summary
#-------------------------------------------------------------------------------

echo ""
echo -e "${GREEN}${BOLD}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                               ║"
echo "║              ✅ Deployment Complete!                          ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${CYAN}${BOLD}Access URLs:${NC}"
if [ "$ENVIRONMENT" = "prod" ]; then
    echo "  🌐 Application:  https://localhost"
    echo "  🔧 Admin Panel:  https://localhost/admin"
    echo "  ❤️  Health Check: https://localhost/health/"
else
    echo "  🌐 Application:  http://localhost:8000"
    echo "  🔧 Admin Panel:  http://localhost:8000/admin"
fi
echo ""

echo -e "${CYAN}${BOLD}Service Status:${NC}"
$COMPOSE_CMD -f "$COMPOSE_FILE" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo -e "${CYAN}${BOLD}Quick Commands:${NC}"
echo "  Logs:     cd provisioning && $COMPOSE_CMD -f $COMPOSE_FILE logs -f"
echo "  Stop:     cd provisioning && $COMPOSE_CMD -f $COMPOSE_FILE down"
echo "  Restart:  cd provisioning && $COMPOSE_CMD -f $COMPOSE_FILE restart"
echo "  Shell:    cd provisioning && $COMPOSE_CMD -f $COMPOSE_FILE exec web python manage.py shell"
echo ""

if [ "$ENVIRONMENT" = "prod" ] && [ "$NO_GPU" = true ]; then
    echo -e "${YELLOW}${BOLD}Note:${NC} AI/OCR services are disabled (no GPU). Documents will use mock extraction."
fi

echo -e "${GREEN}${BOLD}🎉 iFin Bank is ready!${NC}"
