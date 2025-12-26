# iFin Bank Verification System

An AI-powered automated verification platform for financial institutions, designed to streamline customer onboarding verification using DeepSeek-OCR and vLLM.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Django](https://img.shields.io/badge/Django-5.2+-green.svg)
![License](https://img.shields.io/badge/License-Proprietary-red.svg)

---

## 📋 Table of Contents

- [Quick Start Guide](#-quick-start-guide)
- [Features](#-features)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [AI Services Setup](#-ai-services-setup)
- [Configuration](#-configuration)
- [Verification Workflow](#-verification-workflow)
- [API Reference](#-api-reference)
- [Testing](#-testing)
- [Documentation](#-documentation)

---

## 🚀 Quick Start Guide

Get the iFin Bank Verification System running in under 5 minutes.

### ⚡ One-Step Deployment (Recommended)

```bash
# Linux/Mac
chmod +x deploy.sh && ./deploy.sh

# Windows
deploy.bat
```

The script will prompt you to choose an environment and automatically:
- ✅ Check prerequisites (Docker, GPU)
- ✅ Generate secure configuration
- ✅ Build Docker containers
- ✅ Start all services
- ✅ Run database migrations
- ✅ Seed compliance policies
- ✅ Create admin user

**Or use make commands:**

```bash
make deploy-dev        # Development environment
make deploy-prod       # Production with vLLM/GPU
make deploy-prod-no-gpu  # Production without GPU
```

---

### 📋 Local Setup (Without Docker)

For local development without Docker:

### 📋 Manual Setup

If you prefer manual setup, follow these steps:

### Prerequisites


| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.10+ | Required |
| Django | 5.2+ | Auto-installed |
| CUDA | 11.8+ | For GPU inference (optional) |
| GPU Memory | 40GB+ | For DeepSeek-OCR (optional) |

### Step 1: Clone & Setup Environment

```bash
# Clone the repository
git clone <repository-url>
cd ifinbank

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

### Step 2: Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt
```

### Step 3: Initialize Database

```bash
# Run database migrations
python manage.py migrate

# Seed compliance policies (KYC, AML, Document Standards)
python manage.py seed_policies
```

### Step 4: Create Admin User

```bash
# Create superuser account
python manage.py createsuperuser

# Follow prompts to enter:
# - Email address
# - First name
# - Last name  
# - Password
```

### Step 5: Start Development Server

```bash
python manage.py runserver
```

### Step 6: Access the Application

| URL | Description |
|-----|-------------|
| http://localhost:8000 | Main Application |
| http://localhost:8000/admin | Django Admin Panel |

### 🎉 You're Ready!

Login with your superuser credentials and start verifying customers.

---

## ⚡ Quick Start with AI Services (Optional)

For full AI-powered OCR capabilities, set up vLLM with DeepSeek-OCR:

### Option A: Quick Setup (Nightly Build)

```bash
# Install vLLM with DeepSeek-OCR support
pip install -U vllm --pre --extra-index-url https://wheels.vllm.ai/nightly

# Start vLLM server (requires GPU)
python -m vllm.entrypoints.openai.api_server \
    --model deepseek-ai/DeepSeek-OCR \
    --trust-remote-code \
    --port 8001
```

### Option B: Using Docker

```bash
docker run --gpus all -p 8001:8000 \
    vllm/vllm-openai:latest \
    --model deepseek-ai/DeepSeek-OCR \
    --trust-remote-code
```

### Configure Environment

Create a `.env` file in the project root:

```env
# vLLM Configuration
VLLM_API_URL=http://localhost:8001
VLLM_MODEL_NAME=deepseek-ai/DeepSeek-OCR
USE_VLLM_OCR=true

# ChromaDB (for semantic policy search)
USE_CHROMADB=true
```

### Sync Policies to ChromaDB

```bash
python manage.py sync_policies
```

> **Note:** The system works without AI services using mock data for development/testing.

---

## 🌟 Features

| Feature | Description |
|---------|-------------|
| 🔍 **DeepSeek-OCR Integration** | State-of-the-art document OCR via vLLM |
| 🎯 **Advanced Field Comparison** | Multi-strategy matching (fuzzy, phonetic, OCR-tolerant) |
| 📚 **RAG-Enhanced Compliance** | ChromaDB-powered semantic policy search |
| ⚖️ **Intelligent Scoring** | Weighted scoring with automatic decision logic |
| 📝 **Complete Audit Trail** | Full logging of all verification steps |
| 🌙 **Modern Dark UI** | Premium dark-themed responsive interface |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    iFin Bank Verification System                 │
├─────────────────────────────────────────────────────────────────┤
│  Frontend (Django Templates + Modern CSS)                       │
├─────────────────────────────────────────────────────────────────┤
│  Django REST API                                                │
├──────────────┬──────────────┬──────────────┬───────────────────┤
│ Verification │  Documents   │  Compliance  │     Accounts      │
│   Engine     │   (OCR)      │   (RAG)      │                   │
├──────────────┼──────────────┼──────────────┼───────────────────┤
│              │   vLLM +     │   ChromaDB   │   SQLite/         │
│              │ DeepSeek-OCR │  (Vectors)   │   PostgreSQL      │
└──────────────┴──────────────┴──────────────┴───────────────────┘
```

---

## 📁 Project Structure

```
ifinbank/
├── apps/
│   ├── core/                  # Shared models and utilities
│   ├── accounts/              # User management & authentication
│   ├── verification/          # Verification engine & workflows
│   ├── documents/             # Document processing & OCR
│   └── compliance/            # Regulatory compliance & policies
│
├── config/                    # Django settings
├── templates/                 # HTML templates
├── static/                    # CSS, JS, images
├── docs/                      # Documentation
├── .specs/                    # Design specifications
└── requirements.txt
```

---

## 🤖 AI Services Setup

### DeepSeek-OCR via vLLM

| Resource | Link |
|----------|------|
| DeepSeek-OCR | https://github.com/deepseek-ai/DeepSeek-OCR |
| vLLM | https://github.com/vllm-project/vllm |
| HuggingFace Model | https://huggingface.co/deepseek-ai/DeepSeek-OCR |

**Supported OCR Modes:**
- Free OCR - Extract text without layout
- Document-to-Markdown - Preserve document structure
- Figure Parsing - Understand charts/diagrams
- Grounded OCR - Locate specific text

See [docs/VLLM_SETUP.md](docs/VLLM_SETUP.md) for detailed setup instructions.

### ChromaDB for RAG

```bash
# Install ChromaDB
pip install chromadb sentence-transformers

# Sync policies
python manage.py sync_policies
```

---

## ⚙️ Configuration

### Environment Variables

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=True

# vLLM Server
VLLM_API_URL=http://localhost:8001
VLLM_MODEL_NAME=deepseek-ai/DeepSeek-OCR
VLLM_TIMEOUT=120

# ChromaDB
CHROMADB_HOST=localhost
CHROMADB_PORT=8000
CHROMADB_COLLECTION=ifinbank_policies

# Verification Thresholds
VERIFICATION_AUTO_APPROVE=85.0
VERIFICATION_REVIEW=70.0
VERIFICATION_AUTO_REJECT=50.0

# Feature Flags
USE_VLLM_OCR=true
USE_CHROMADB=true
```

---

## 🔄 Verification Workflow

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Request    │───▶│   Document   │───▶│     OCR      │
│   Created    │    │   Upload     │    │  Processing  │
└──────────────┘    └──────────────┘    └──────────────┘
                                               │
       ┌───────────────────────────────────────┘
       ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│     Data     │───▶│  Compliance  │───▶│   Scoring    │
│  Comparison  │    │    Checks    │    │  & Decision  │
└──────────────┘    └──────────────┘    └──────────────┘
```

### Decision Thresholds

| Score | Decision | Action |
|-------|----------|--------|
| ≥ 85% | ✅ Auto-Approve | Verification completed |
| 70-84% | 🔍 Manual Review | Assigned to officer |
| 50-69% | ⚠️ Supervisor Review | Escalated |
| < 50% | ❌ Auto-Reject | Application denied |

---

## 🔒 User Roles

| Role | Permissions |
|------|-------------|
| **Verification Officer** | Create, view, process verifications |
| **Supervisor** | Review, approve, reject verifications |
| **Admin** | Full access, manage users and policies |

---

## 📊 API Reference

### Verification Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/verification/` | Dashboard |
| GET | `/verification/requests/` | List all requests |
| POST | `/verification/requests/create/` | Create new request |
| GET | `/verification/requests/<id>/` | View request details |
| POST | `/verification/requests/<id>/process/` | Process verification |
| POST | `/verification/requests/<id>/approve/` | Approve request |
| POST | `/verification/requests/<id>/reject/` | Reject request |

### Document Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/documents/upload/` | Upload document |
| POST | `/documents/<id>/process/` | Run OCR processing |
| GET | `/documents/<id>/extraction/` | Get extraction data |

### Compliance Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/compliance/policies/` | List policies |
| GET | `/compliance/check/<request_id>/` | Run compliance check |

---

## 🧪 Testing

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test apps.verification.tests

# Run with verbosity
python manage.py test -v 2

# With pytest
pytest apps/verification/tests/
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [VLLM_SETUP.md](docs/VLLM_SETUP.md) | vLLM & DeepSeek-OCR setup guide |
| [project-overview.md](.specs/project-overview.md) | Project overview |
| [models-spec.md](.specs/models-spec.md) | Database models specification |
| [api-spec.md](.specs/api-spec.md) | API endpoints specification |
| [ui-spec.md](.specs/ui-spec.md) | UI/UX specification |

---

## 🛠️ Development Commands

```bash
# Database
python manage.py makemigrations    # Create migrations
python manage.py migrate           # Apply migrations

# Policies
python manage.py seed_policies     # Seed initial policies
python manage.py sync_policies     # Sync to ChromaDB
python manage.py sync_policies --clean  # Clean and resync

# Code Quality
black apps/                        # Format code
isort apps/                        # Sort imports
flake8 apps/                       # Lint code

# Server
python manage.py runserver         # Development server
python manage.py runserver 0.0.0.0:8000  # Accessible on network
```

---

## 🐛 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| Database errors | Run `python manage.py migrate` |
| vLLM connection failed | Check vLLM server is running on correct port |
| ChromaDB errors | Ensure `chromadb` package is installed |

### Get Help

- Check [docs/VLLM_SETUP.md](docs/VLLM_SETUP.md) for AI service issues
- Review Django logs in `logs/ifinbank.log`

---

## 📄 License

Proprietary - iFin Bank © 2024

---

<p align="center">
  Built with ❤️ for iFin Bank<br>
  Powered by <a href="https://github.com/deepseek-ai/DeepSeek-OCR">DeepSeek-OCR</a> & <a href="https://github.com/vllm-project/vllm">vLLM</a>
</p>
