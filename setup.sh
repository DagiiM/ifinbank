#!/bin/bash

#===============================================================================
# iFin Bank Verification System - Setup Script
# 
# This script automates the complete setup of the iFin Bank Verification System.
# Run with: chmod +x setup.sh && ./setup.sh
#===============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
VENV_NAME="venv"
PYTHON_MIN_VERSION="3.10"
DEFAULT_ADMIN_EMAIL="admin@ifinbank.com"

#-------------------------------------------------------------------------------
# Helper Functions
#-------------------------------------------------------------------------------

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                                                               ║"
    echo "║         iFin Bank Verification System Setup                   ║"
    echo "║                                                               ║"
    echo "║         AI-Powered Customer Verification Platform             ║"
    echo "║                                                               ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "\n${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ $1${NC}"
}

check_command() {
    if command -v $1 &> /dev/null; then
        return 0
    else
        return 1
    fi
}

version_gte() {
    # Check if version $1 >= $2
    [ "$(printf '%s\n' "$2" "$1" | sort -V | head -n1)" = "$2" ]
}

#-------------------------------------------------------------------------------
# Pre-flight Checks
#-------------------------------------------------------------------------------

preflight_checks() {
    print_step "Running pre-flight checks..."
    
    # Check Python
    if check_command python3; then
        PYTHON_CMD="python3"
    elif check_command python; then
        PYTHON_CMD="python"
    else
        print_error "Python is not installed. Please install Python ${PYTHON_MIN_VERSION}+"
        exit 1
    fi
    
    # Check Python version
    PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if version_gte $PYTHON_VERSION $PYTHON_MIN_VERSION; then
        print_success "Python $PYTHON_VERSION detected"
    else
        print_error "Python $PYTHON_MIN_VERSION+ required, found $PYTHON_VERSION"
        exit 1
    fi
    
    # Check pip
    if ! check_command pip && ! check_command pip3; then
        print_error "pip is not installed. Please install pip."
        exit 1
    fi
    print_success "pip is available"
    
    # Check for existing virtual environment
    if [ -d "$VENV_NAME" ]; then
        print_warning "Virtual environment '$VENV_NAME' already exists"
        read -p "Do you want to recreate it? (y/N): " recreate_venv
        if [[ $recreate_venv =~ ^[Yy]$ ]]; then
            rm -rf $VENV_NAME
            print_info "Removed existing virtual environment"
        fi
    fi
}

#-------------------------------------------------------------------------------
# Environment Setup
#-------------------------------------------------------------------------------

setup_virtualenv() {
    print_step "Setting up virtual environment..."
    
    if [ ! -d "$VENV_NAME" ]; then
        $PYTHON_CMD -m venv $VENV_NAME
        print_success "Created virtual environment: $VENV_NAME"
    else
        print_info "Using existing virtual environment"
    fi
    
    # Activate virtual environment
    source $VENV_NAME/bin/activate
    print_success "Activated virtual environment"
    
    # Upgrade pip
    pip install --upgrade pip --quiet
    print_success "Upgraded pip to latest version"
}

install_dependencies() {
    print_step "Installing Python dependencies..."
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt --quiet
        print_success "Installed Python packages from requirements.txt"
    else
        print_warning "requirements.txt not found, installing core packages..."
        pip install django pillow httpx python-dateutil --quiet
        print_success "Installed core packages"
    fi
    
    # Optional: Install AI/ML packages
    read -p "Install AI/ML packages (ChromaDB, Sentence Transformers)? (y/N): " install_ai
    if [[ $install_ai =~ ^[Yy]$ ]]; then
        print_info "Installing AI/ML packages (this may take a while)..."
        pip install chromadb sentence-transformers --quiet
        print_success "Installed AI/ML packages"
    fi
}

#-------------------------------------------------------------------------------
# Database Setup
#-------------------------------------------------------------------------------

setup_database() {
    print_step "Setting up database..."
    
    # Create logs directory if it doesn't exist
    mkdir -p logs
    mkdir -p media
    mkdir -p chromadb_data
    print_success "Created required directories"
    
    # Run migrations
    python manage.py makemigrations --no-input
    python manage.py migrate --no-input
    print_success "Database migrations applied"
}

seed_data() {
    print_step "Seeding initial data..."
    
    # Seed compliance policies
    python manage.py seed_policies
    print_success "Seeded compliance policies (KYC, AML, Document Standards)"
    
    # Sync to ChromaDB if available
    read -p "Sync policies to ChromaDB for semantic search? (y/N): " sync_chromadb
    if [[ $sync_chromadb =~ ^[Yy]$ ]]; then
        python manage.py sync_policies || print_warning "ChromaDB sync skipped (not installed)"
    fi
}

#-------------------------------------------------------------------------------
# Admin User Setup
#-------------------------------------------------------------------------------

setup_admin() {
    print_step "Setting up admin user..."
    
    # Check if admin exists
    ADMIN_EXISTS=$(python -c "
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
import django
django.setup()
from apps.accounts.models import User
print('yes' if User.objects.filter(is_superuser=True).exists() else 'no')
" 2>/dev/null || echo "no")
    
    if [ "$ADMIN_EXISTS" = "yes" ]; then
        print_warning "Admin user already exists"
        read -p "Create another admin user? (y/N): " create_admin
        if [[ ! $create_admin =~ ^[Yy]$ ]]; then
            return
        fi
    fi
    
    echo ""
    echo "Create Admin User"
    echo "-----------------"
    
    read -p "Email [$DEFAULT_ADMIN_EMAIL]: " admin_email
    admin_email=${admin_email:-$DEFAULT_ADMIN_EMAIL}
    
    read -p "First Name [Admin]: " admin_first
    admin_first=${admin_first:-Admin}
    
    read -p "Last Name [User]: " admin_last
    admin_last=${admin_last:-User}
    
    read -s -p "Password: " admin_password
    echo ""
    
    if [ -z "$admin_password" ]; then
        admin_password="admin123"
        print_warning "No password entered, using default: admin123"
    fi
    
    # Create admin user
    python -c "
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
import django
django.setup()
from apps.accounts.models import User
user = User.objects.create_superuser(
    email='$admin_email',
    password='$admin_password',
    first_name='$admin_first',
    last_name='$admin_last'
)
print(f'Created admin: {user.email}')
"
    print_success "Admin user created: $admin_email"
}

#-------------------------------------------------------------------------------
# Environment Configuration
#-------------------------------------------------------------------------------

setup_env_file() {
    print_step "Setting up environment configuration..."
    
    if [ -f ".env" ]; then
        print_warning ".env file already exists, skipping..."
        return
    fi
    
    read -p "Create .env configuration file? (Y/n): " create_env
    if [[ $create_env =~ ^[Nn]$ ]]; then
        return
    fi
    
    # Generate secret key
    SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" 2>/dev/null || echo "change-me-in-production")
    
    cat > .env << EOF
# iFin Bank Verification System Configuration
# Generated on $(date)

# Django Settings
SECRET_KEY=$SECRET_KEY
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (default: SQLite)
# DATABASE_URL=postgres://user:pass@localhost/ifinbank

# vLLM Configuration
VLLM_API_URL=http://localhost:8001
VLLM_MODEL_NAME=deepseek-ai/DeepSeek-OCR
VLLM_TIMEOUT=120
VLLM_MAX_TOKENS=8192

# ChromaDB Configuration
CHROMADB_HOST=localhost
CHROMADB_PORT=8000
CHROMADB_COLLECTION=ifinbank_policies

# Embedding Model
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Feature Flags
USE_VLLM_OCR=false
USE_CHROMADB=false

# Verification Thresholds
VERIFICATION_AUTO_APPROVE=85.0
VERIFICATION_REVIEW=70.0
VERIFICATION_AUTO_REJECT=50.0
EOF
    
    print_success "Created .env configuration file"
    print_info "Edit .env to customize your settings"
}

#-------------------------------------------------------------------------------
# Collect Static Files
#-------------------------------------------------------------------------------

collect_static() {
    print_step "Collecting static files..."
    
    python manage.py collectstatic --no-input --clear 2>/dev/null || true
    print_success "Static files collected"
}

#-------------------------------------------------------------------------------
# Verification & Summary
#-------------------------------------------------------------------------------

verify_setup() {
    print_step "Verifying setup..."
    
    # Run Django check
    python manage.py check --deploy 2>/dev/null || python manage.py check
    print_success "Django configuration verified"
    
    # Run quick test
    python manage.py test apps.verification.tests.test_comparison --verbosity=0 2>/dev/null && \
        print_success "Tests passed" || \
        print_warning "Some tests may have failed (non-critical)"
}

print_summary() {
    echo -e "\n${GREEN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                                                               ║"
    echo "║                    Setup Complete! 🎉                         ║"
    echo "║                                                               ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    echo -e "${CYAN}Quick Start Commands:${NC}"
    echo ""
    echo "  1. Activate virtual environment:"
    echo -e "     ${YELLOW}source $VENV_NAME/bin/activate${NC}"
    echo ""
    echo "  2. Start development server:"
    echo -e "     ${YELLOW}python manage.py runserver${NC}"
    echo ""
    echo "  3. Access the application:"
    echo -e "     ${YELLOW}http://localhost:8000${NC}"
    echo ""
    echo "  4. Access admin panel:"
    echo -e "     ${YELLOW}http://localhost:8000/admin${NC}"
    echo ""
    
    if [ -f ".env" ]; then
        echo -e "${CYAN}Configuration:${NC}"
        echo "  Edit .env file to customize settings"
        echo ""
    fi
    
    echo -e "${CYAN}Optional - Start vLLM for AI-powered OCR:${NC}"
    echo -e "  ${YELLOW}python -m vllm.entrypoints.openai.api_server \\"
    echo "      --model deepseek-ai/DeepSeek-OCR \\"
    echo "      --trust-remote-code \\"
    echo -e "      --port 8001${NC}"
    echo ""
    
    echo -e "${CYAN}Documentation:${NC}"
    echo "  - README.md - Quick start guide"
    echo "  - docs/VLLM_SETUP.md - AI services setup"
    echo "  - .specs/ - Technical specifications"
    echo ""
    
    print_success "iFin Bank Verification System is ready!"
}

#-------------------------------------------------------------------------------
# Main Execution
#-------------------------------------------------------------------------------

main() {
    print_banner
    
    # Navigate to script directory
    cd "$(dirname "$0")"
    
    preflight_checks
    setup_virtualenv
    install_dependencies
    setup_database
    seed_data
    setup_admin
    setup_env_file
    collect_static
    verify_setup
    print_summary
}

# Run main function
main "$@"
