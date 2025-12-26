# iFin Bank Verification System - Project Overview

> **Version:** 1.0  
> **Created:** December 26, 2024  
> **Status:** In Development

---

## Project Summary

The iFin Bank Verification System is an AI-powered automated verification platform designed to streamline customer onboarding verification for financial institutions. The system validates data entered by Account Opening Officers against source documents and regulatory requirements.

### Key Principles

1. **Verification Only** - This system handles verification, not data entry
2. **AI-Powered** - Uses DeepSeek OCR and vLLM for document intelligence
3. **Compliance-First** - Built-in KYC/AML and policy compliance checking
4. **Audit Trail** - Complete logging of all verification decisions

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Backend Framework | Django 5.x | Application logic, API, user management |
| OCR Engine | DeepSeek + vLLM | Document reading, text extraction |
| Vector Database | ChromaDB | Policy embeddings, semantic search |
| Database | PostgreSQL | Transactional data, audit logs |
| Cache/Queue | Redis | Task queue, caching |
| Frontend | Django Templates + HTMX | Dynamic UI without SPA complexity |

---

## Core Applications

### 1. `core` - Shared Functionality
- Base models (BaseModel with audit fields)
- Common utilities and mixins
- Shared template tags and filters

### 2. `accounts` - User Management
- Custom User model
- Role-based access control (Verification Officer, Supervisor, Admin)
- Authentication and authorization

### 3. `verification` - Verification Engine
- VerificationRequest model
- VerificationResult and Discrepancy tracking
- Verification workflow orchestration

### 4. `documents` - Document Processing
- Document storage and management
- OCR integration with DeepSeek
- Field extraction pipelines

### 5. `compliance` - Regulatory Compliance
- Policy management with ChromaDB
- KYC/AML checking
- Rule engine for standard checks

---

## User Roles

| Role | Permissions |
|------|-------------|
| Verification Officer | View/process verification requests, review documents |
| Supervisor | All officer permissions + approve/reject, manage queue |
| Admin | Full system access, user management, policy configuration |

---

## Key Workflows

### Verification Workflow

```
┌─────────────────────┐
│ Customer Data from  │
│ Core Banking System │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Create Verification │
│      Request        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Upload/Retrieve    │
│ Source Documents    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   OCR Processing    │
│  (DeepSeek + vLLM)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Data-to-Document    │
│    Comparison       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Compliance Checks  │
│ (KYC/AML/Policy)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────┐
│          Score Calculation           │
└──────┬──────────────┬───────────────┘
       │              │
    ≥85%           70-85%           <70%
       │              │               │
       ▼              ▼               ▼
┌──────────┐    ┌──────────┐    ┌──────────┐
│ Auto     │    │ Manual   │    │ Auto     │
│ Approve  │    │ Review   │    │ Reject   │
└──────────┘    └──────────┘    └──────────┘
```

---

## Project Structure

```
ifinbank/
├── config/                 # Django project configuration
│   ├── settings/
│   │   ├── base.py        # Base settings
│   │   ├── development.py # Development settings
│   │   └── production.py  # Production settings
│   ├── urls.py            # Root URL configuration
│   └── wsgi.py
├── apps/                   # Django applications
│   ├── core/              # Shared functionality
│   ├── accounts/          # User management
│   ├── verification/      # Verification engine
│   ├── documents/         # Document processing
│   └── compliance/        # Regulatory compliance
├── templates/             # HTML templates
│   ├── base.html
│   ├── verification/
│   ├── documents/
│   └── compliance/
├── static/                # Static assets
│   ├── css/
│   ├── js/
│   └── images/
├── media/                 # User uploads
├── tests/                 # Test suite
├── .specs/                # Project specifications
└── manage.py
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Verification Accuracy | 99%+ |
| Processing Time | < 30 minutes |
| False Positive Rate | < 1% |
| False Negative Rate | < 0.1% |
| System Availability | 99.9% |

---

## Implementation Phases

1. **Phase 1: Foundation** (Weeks 1-2)
   - Django project setup
   - Core models and authentication
   - Basic UI structure

2. **Phase 2: Document Intelligence** (Weeks 3-4)
   - Document upload and storage
   - OCR integration
   - Field extraction

3. **Phase 3: Verification Engine** (Weeks 5-6)
   - Comparison algorithms
   - Scoring engine
   - Workflow automation

4. **Phase 4: Compliance Engine** (Weeks 7-8)
   - Policy management
   - KYC/AML checks
   - ChromaDB integration
