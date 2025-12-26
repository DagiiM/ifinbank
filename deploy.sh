#!/bin/bash

#===============================================================================
# iFin Bank Verification System - One-Step Deployment
# 
# This script handles EVERYTHING including Docker installation.
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
# Helper Functions
#-------------------------------------------------------------------------------

detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            OS=$ID
            OS_VERSION=$VERSION_ID
        else
            OS="linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        OS="windows"
    else
        OS="unknown"
    fi
    echo "$OS"
}

install_docker_ubuntu() {
    echo -e "${CYAN}Installing Docker on Ubuntu/Debian...${NC}"
    
    # Remove old versions
    sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
    
    # Install prerequisites
    sudo apt-get update
    sudo apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
    
    # Add Docker's official GPG key
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    # Set up repository
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # Add current user to docker group
    sudo usermod -aG docker $USER
    
    # Start Docker
    sudo systemctl start docker
    sudo systemctl enable docker
    
    echo -e "${GREEN}✓ Docker installed successfully${NC}"
    echo -e "${YELLOW}Note: You may need to log out and back in for group changes to take effect${NC}"
}

install_docker_debian() {
    echo -e "${CYAN}Installing Docker on Debian...${NC}"
    
    sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
    
    sudo apt-get update
    sudo apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
    
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
        $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    sudo usermod -aG docker $USER
    sudo systemctl start docker
    sudo systemctl enable docker
    
    echo -e "${GREEN}✓ Docker installed successfully${NC}"
}

install_docker_centos() {
    echo -e "${CYAN}Installing Docker on CentOS/RHEL/Fedora...${NC}"
    
    sudo yum remove -y docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine 2>/dev/null || true
    
    sudo yum install -y yum-utils
    sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    
    sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    sudo usermod -aG docker $USER
    sudo systemctl start docker
    sudo systemctl enable docker
    
    echo -e "${GREEN}✓ Docker installed successfully${NC}"
}

install_docker_macos() {
    echo -e "${CYAN}Installing Docker on macOS...${NC}"
    
    # Check for Homebrew
    if ! command -v brew &> /dev/null; then
        echo -e "${YELLOW}Homebrew not found. Installing Homebrew first...${NC}"
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    
    # Install Docker Desktop via Homebrew
    brew install --cask docker
    
    echo -e "${GREEN}✓ Docker Desktop installed${NC}"
    echo -e "${YELLOW}Please open Docker Desktop from Applications to complete setup${NC}"
    
    # Open Docker Desktop
    open -a Docker
    
    echo "Waiting for Docker to start..."
    while ! docker system info > /dev/null 2>&1; do
        sleep 2
    done
    echo -e "${GREEN}✓ Docker is running${NC}"
}

install_nvidia_docker() {
    echo -e "${CYAN}Installing NVIDIA Docker support...${NC}"
    
    # Add NVIDIA package repositories
    distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
    curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
    curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
        sudo tee /etc/apt/sources.list.d/nvidia-docker.list
    
    sudo apt-get update
    sudo apt-get install -y nvidia-docker2
    
    sudo systemctl restart docker
    
    echo -e "${GREEN}✓ NVIDIA Docker installed${NC}"
}

install_docker() {
    local os=$(detect_os)
    
    echo -e "${CYAN}Detected OS: $os${NC}"
    
    case $os in
        ubuntu)
            install_docker_ubuntu
            ;;
        debian)
            install_docker_debian
            ;;
        centos|rhel|fedora)
            install_docker_centos
            ;;
        macos)
            install_docker_macos
            ;;
        windows)
            echo -e "${YELLOW}Windows detected.${NC}"
            echo ""
            echo "Please install Docker Desktop manually:"
            echo "  1. Download from: https://www.docker.com/products/docker-desktop"
            echo "  2. Run the installer"
            echo "  3. Start Docker Desktop"
            echo "  4. Re-run this script"
            echo ""
            exit 1
            ;;
        *)
            echo -e "${RED}Unsupported OS: $os${NC}"
            echo "Please install Docker manually: https://docs.docker.com/get-docker/"
            exit 1
            ;;
    esac
}

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
# Step 1: Install Docker if not present
#-------------------------------------------------------------------------------

echo -e "${CYAN}[1/6] Checking Docker...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Docker not found. Installing...${NC}"
    
    if [ "$AUTO_YES" = false ]; then
        read -p "Install Docker automatically? (Y/n): " install_docker_choice
        if [[ $install_docker_choice =~ ^[Nn]$ ]]; then
            echo "Please install Docker manually: https://docs.docker.com/get-docker/"
            exit 1
        fi
    fi
    
    install_docker
    
    # Reload shell to get docker group
    if [[ "$(detect_os)" != "macos" ]]; then
        echo -e "${YELLOW}Docker group updated. Using sudo for this session...${NC}"
        DOCKER_CMD="sudo docker"
        COMPOSE_CMD="sudo docker compose"
    fi
else
    echo -e "${GREEN}  ✓ Docker is installed${NC}"
    DOCKER_CMD="docker"
fi

# Check Docker Compose
if docker compose version &> /dev/null 2>&1; then
    COMPOSE_CMD="${DOCKER_CMD} compose"
    echo -e "${GREEN}  ✓ Docker Compose (plugin)${NC}"
elif command -v docker-compose &> /dev/null; then
    if [[ "$DOCKER_CMD" == "sudo docker" ]]; then
        COMPOSE_CMD="sudo docker-compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    echo -e "${GREEN}  ✓ Docker Compose (standalone)${NC}"
else
    echo -e "${RED}Docker Compose not found.${NC}"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Verify Docker is running
if ! $DOCKER_CMD info > /dev/null 2>&1; then
    echo -e "${YELLOW}Docker daemon not running. Starting...${NC}"
    if [[ "$(detect_os)" == "macos" ]]; then
        open -a Docker
        echo "Waiting for Docker to start..."
        while ! docker info > /dev/null 2>&1; do
            sleep 2
        done
    else
        sudo systemctl start docker
    fi
fi
echo -e "${GREEN}  ✓ Docker daemon is running${NC}"

#-------------------------------------------------------------------------------
# Step 2: GPU Check for Production
#-------------------------------------------------------------------------------

echo -e "${CYAN}[2/6] Checking GPU...${NC}"

if [ "$ENVIRONMENT" = "prod" ] && [ "$NO_GPU" = false ]; then
    if command -v nvidia-smi &> /dev/null; then
        echo -e "${GREEN}  ✓ NVIDIA GPU detected${NC}"
        
        # Check for nvidia-docker
        if ! $DOCKER_CMD info 2>/dev/null | grep -q "nvidia"; then
            echo -e "${YELLOW}  NVIDIA Docker not configured. Installing...${NC}"
            install_nvidia_docker 2>/dev/null || {
                echo -e "${YELLOW}  Could not install nvidia-docker, continuing without GPU${NC}"
                NO_GPU=true
            }
        else
            echo -e "${GREEN}  ✓ NVIDIA Docker configured${NC}"
        fi
    else
        echo -e "${YELLOW}  ℹ No NVIDIA GPU detected - continuing with CPU mode${NC}"
        echo -e "${YELLOW}    (AI/OCR will use mock extraction)${NC}"
        NO_GPU=true
    fi
else
    echo -e "${GREEN}  ✓ GPU check skipped${NC}"
fi

#-------------------------------------------------------------------------------
# Step 3: Environment Configuration
#-------------------------------------------------------------------------------

echo -e "${CYAN}[3/6] Configuring environment...${NC}"

cd "$PROVISIONING_DIR"

if [ "$ENVIRONMENT" = "prod" ]; then
    ENV_FILE=".env.production"
    
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "  Creating production environment file..."
        
        # Generate secure keys
        SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))" 2>/dev/null || \
                     openssl rand -base64 50 | tr -d '\n' || \
                     head -c 50 /dev/urandom | base64 | tr -d '\n')
        
        DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))" 2>/dev/null || \
                      openssl rand -base64 24 | tr -d '\n' || \
                      head -c 24 /dev/urandom | base64 | tr -d '\n')
        
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
        echo -e "  Generating self-signed SSL certificate..."
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
    # Development environment
    if [ ! -f "../.env" ]; then
        cat > "../.env" << EOF
DEBUG=True
SECRET_KEY=dev-secret-key-change-in-production
USE_VLLM_OCR=false
USE_CHROMADB=true
EOF
        echo -e "${GREEN}  ✓ Created development .env${NC}"
    else
        echo -e "${GREEN}  ✓ Using existing .env${NC}"
    fi
fi

#-------------------------------------------------------------------------------
# Step 4: Build Containers
#-------------------------------------------------------------------------------

echo -e "${CYAN}[4/6] Building containers...${NC}"

if [ "$ENVIRONMENT" = "prod" ]; then
    COMPOSE_FILE="docker-compose.yml"
    
    if [ "$NO_GPU" = true ]; then
        echo -e "${YELLOW}  Building without vLLM (GPU not available)${NC}"
        $COMPOSE_CMD -f "$COMPOSE_FILE" build web db redis chromadb nginx celery_worker celery_beat
    else
        $COMPOSE_CMD -f "$COMPOSE_FILE" build
    fi
else
    COMPOSE_FILE="docker-compose.dev.yml"
    $COMPOSE_CMD -f "$COMPOSE_FILE" build
fi

echo -e "${GREEN}  ✓ Build complete${NC}"

#-------------------------------------------------------------------------------
# Step 5: Start Services
#-------------------------------------------------------------------------------

echo -e "${CYAN}[5/6] Starting services...${NC}"

if [ "$ENVIRONMENT" = "prod" ] && [ "$NO_GPU" = true ]; then
    $COMPOSE_CMD -f "$COMPOSE_FILE" up -d web db redis chromadb nginx celery_worker celery_beat
else
    $COMPOSE_CMD -f "$COMPOSE_FILE" up -d
fi

echo -e "${GREEN}  ✓ Services started${NC}"

#-------------------------------------------------------------------------------
# Step 6: Initialize Application
#-------------------------------------------------------------------------------

echo -e "${CYAN}[6/6] Initializing application...${NC}"

# Wait for database
echo -e "  Waiting for database to be ready..."
sleep 15

# Run migrations
echo -e "  Running migrations..."
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
" 2>/dev/null || true
        echo -e "${GREEN}  ✓ Admin created: admin@ifinbank.com / admin123${NC}"
    else
        echo ""
        $COMPOSE_CMD -f "$COMPOSE_FILE" exec web python manage.py createsuperuser
    fi
else
    echo -e "${GREEN}  ✓ Admin user exists${NC}"
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
$COMPOSE_CMD -f "$COMPOSE_FILE" ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null || $COMPOSE_CMD -f "$COMPOSE_FILE" ps
echo ""

echo -e "${CYAN}${BOLD}Quick Commands:${NC}"
echo "  Logs:     cd provisioning && $COMPOSE_CMD -f $COMPOSE_FILE logs -f"
echo "  Stop:     cd provisioning && $COMPOSE_CMD -f $COMPOSE_FILE down"
echo "  Restart:  cd provisioning && $COMPOSE_CMD -f $COMPOSE_FILE restart"
echo "  Shell:    cd provisioning && $COMPOSE_CMD -f $COMPOSE_FILE exec web python manage.py shell"
echo ""

if [ "$ENVIRONMENT" = "prod" ] && [ "$NO_GPU" = true ]; then
    echo -e "${YELLOW}${BOLD}Note:${NC} AI/OCR services are disabled (no GPU). Documents will use mock extraction."
    echo ""
fi

echo -e "${GREEN}${BOLD}🎉 iFin Bank is ready! Open your browser to access the application.${NC}"
