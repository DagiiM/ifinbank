# iFin Bank - API Specification

> **Version:** 1.0  
> **Last Updated:** December 26, 2024

---

## API Overview

The iFin Bank Verification System provides both internal Django views and RESTful API endpoints for integration with core banking systems.

### Base URL
```
Development: http://localhost:8000/api/v1/
Production: https://verify.ifinbank.com/api/v1/
```

### Authentication
All API endpoints require authentication using JWT tokens or session authentication.

---

## Verification Endpoints

### List Verification Requests
```http
GET /api/v1/verification/requests/
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| status | string | Filter by status |
| customer_id | string | Filter by customer |
| priority | int | Filter by priority |
| page | int | Page number |
| page_size | int | Results per page (max 100) |

**Response:**
```json
{
  "count": 150,
  "next": "/api/v1/verification/requests/?page=2",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "customer_id": "CUST001",
      "status": "pending",
      "priority": 5,
      "created_at": "2024-12-26T10:00:00Z",
      "overall_score": null
    }
  ]
}
```

### Create Verification Request
```http
POST /api/v1/verification/requests/
```

**Request Body:**
```json
{
  "customer_id": "CUST001",
  "account_reference": "ACC123456",
  "customer_data": {
    "full_name": "John Doe",
    "id_number": "12345678",
    "date_of_birth": "1990-01-15",
    "address": "123 Main Street",
    "phone": "+254712345678",
    "email": "john.doe@email.com"
  },
  "priority": 5
}
```

**Response:**
```json
{
  "id": "uuid",
  "customer_id": "CUST001",
  "status": "pending",
  "created_at": "2024-12-26T10:00:00Z"
}
```

### Get Verification Request
```http
GET /api/v1/verification/requests/{id}/
```

**Response:**
```json
{
  "id": "uuid",
  "customer_id": "CUST001",
  "account_reference": "ACC123456",
  "status": "completed",
  "priority": 5,
  "customer_data": {...},
  "overall_score": 95.5,
  "is_approved": true,
  "decision_reason": "All verification checks passed",
  "started_at": "2024-12-26T10:01:00Z",
  "completed_at": "2024-12-26T10:05:00Z",
  "results": [...],
  "discrepancies": [...]
}
```

### Process Verification Request
```http
POST /api/v1/verification/requests/{id}/process/
```

Triggers the verification workflow for a pending request.

**Response:**
```json
{
  "id": "uuid",
  "status": "processing",
  "message": "Verification processing started"
}
```

### Approve/Reject Verification
```http
POST /api/v1/verification/requests/{id}/decision/
```

**Request Body:**
```json
{
  "approved": true,
  "reason": "Manual review completed, all checks verified"
}
```

---

## Document Endpoints

### Upload Document
```http
POST /api/v1/documents/upload/
Content-Type: multipart/form-data
```

**Form Data:**
| Field | Type | Description |
|-------|------|-------------|
| verification_request | UUID | Request ID |
| document_type | string | Type of document |
| file | File | Document file |

**Response:**
```json
{
  "id": "uuid",
  "document_type": "national_id",
  "original_filename": "id_front.jpg",
  "status": "uploaded",
  "processing_status": "pending"
}
```

### List Request Documents
```http
GET /api/v1/verification/requests/{id}/documents/
```

**Response:**
```json
{
  "documents": [
    {
      "id": "uuid",
      "document_type": "national_id",
      "original_filename": "id_front.jpg",
      "is_processed": true,
      "page_count": 1,
      "file_url": "/media/verification_docs/..."
    }
  ]
}
```

### Get Document Extraction
```http
GET /api/v1/documents/{id}/extraction/
```

**Response:**
```json
{
  "document_id": "uuid",
  "raw_text": "REPUBLIC OF KENYA\nNATIONAL ID CARD...",
  "structured_data": {
    "full_name": "JOHN DOE",
    "id_number": "12345678",
    "date_of_birth": "1990-01-15"
  },
  "confidence_scores": {
    "full_name": 0.98,
    "id_number": 0.99,
    "date_of_birth": 0.95
  },
  "extraction_method": "ocr"
}
```

---

## Compliance Endpoints

### Run Compliance Check
```http
POST /api/v1/compliance/check/
```

**Request Body:**
```json
{
  "verification_request_id": "uuid"
}
```

**Response:**
```json
{
  "overall_status": "passed",
  "checks": [
    {
      "rule_name": "kyc_id_document",
      "passed": true,
      "score": 100,
      "message": "Valid ID document provided"
    },
    {
      "rule_name": "aml_watchlist",
      "passed": true,
      "score": 100,
      "message": "No watchlist matches found"
    }
  ]
}
```

### List Policies
```http
GET /api/v1/compliance/policies/
```

**Response:**
```json
{
  "policies": [
    {
      "id": "uuid",
      "name": "KYC Requirements",
      "category": "kyc",
      "version": "2.0",
      "effective_date": "2024-01-01",
      "is_active": true
    }
  ]
}
```

---

## Webhook Callbacks

The system can send webhooks for verification events.

### Verification Completed
```json
{
  "event": "verification.completed",
  "timestamp": "2024-12-26T10:05:00Z",
  "data": {
    "verification_id": "uuid",
    "customer_id": "CUST001",
    "status": "completed",
    "is_approved": true,
    "overall_score": 95.5
  }
}
```

### Verification Requires Review
```json
{
  "event": "verification.review_required",
  "timestamp": "2024-12-26T10:05:00Z",
  "data": {
    "verification_id": "uuid",
    "customer_id": "CUST001",
    "reason": "Score below auto-approval threshold",
    "discrepancies_count": 2
  }
}
```

---

## Error Responses

All errors follow a consistent format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request data",
    "details": [
      {
        "field": "customer_id",
        "message": "This field is required"
      }
    ]
  }
}
```

### Error Codes
| Code | HTTP Status | Description |
|------|-------------|-------------|
| VALIDATION_ERROR | 400 | Invalid request data |
| AUTHENTICATION_REQUIRED | 401 | Missing or invalid token |
| PERMISSION_DENIED | 403 | Insufficient permissions |
| NOT_FOUND | 404 | Resource not found |
| ALREADY_PROCESSED | 409 | Request already processed |
| SERVER_ERROR | 500 | Internal server error |

---

## Rate Limits

| Endpoint Type | Limit |
|--------------|-------|
| Read operations | 1000 requests/minute |
| Write operations | 100 requests/minute |
| Document upload | 50 requests/minute |
