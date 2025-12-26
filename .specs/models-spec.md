# iFin Bank - Models Specification

> **Version:** 1.0  
> **Last Updated:** December 26, 2024

---

## Core App Models

### BaseModel (Abstract)

All models inherit from this base class for consistent audit tracking.

```python
class BaseModel(models.Model):
    """Abstract base model with audit fields."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        abstract = True
```

---

## Accounts App Models

### User

Custom user model extending Django's AbstractUser.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| email | EmailField | Unique, used for login |
| phone | CharField | Optional phone number |
| first_name | CharField | User's first name |
| last_name | CharField | User's last name |
| role | CharField | verification_officer / supervisor / admin |
| department | CharField | User's department |
| is_active | BooleanField | Account status |

### Role Choices
- `verification_officer` - Basic verification permissions
- `supervisor` - Review and approve permissions
- `admin` - Full system access

---

## Verification App Models

### VerificationRequest

Main entity for tracking verification requests.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| customer_id | CharField | Reference from core banking |
| account_reference | CharField | Account number if applicable |
| requested_by | ForeignKey | User who initiated the request |
| status | CharField | pending/processing/completed/failed/review_required |
| priority | IntegerField | 1 (highest) to 10 (lowest) |
| customer_data | JSONField | Snapshot of customer data |
| started_at | DateTimeField | When processing began |
| completed_at | DateTimeField | When processing finished |
| overall_score | DecimalField | Final verification score (0-100) |
| is_approved | BooleanField | Final approval decision |
| decision_reason | TextField | Explanation for decision |

#### Status Choices
- `pending` - Awaiting processing
- `processing` - Currently being processed
- `completed` - Processing finished
- `failed` - Processing encountered error
- `review_required` - Needs manual review

### VerificationResult

Individual verification check results.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| request | ForeignKey | Parent verification request |
| check_type | CharField | identity/address/document/compliance/policy |
| check_name | CharField | Specific check identifier |
| score | DecimalField | Check score (0-100) |
| confidence | DecimalField | AI confidence level |
| passed | BooleanField | Whether check passed |
| message | TextField | Human-readable result message |
| evidence | JSONField | Supporting evidence/data |

#### Check Types
- `identity` - Identity verification checks
- `address` - Address verification checks
- `document` - Document authenticity checks
- `compliance` - Regulatory compliance checks
- `policy` - Institutional policy checks

### Discrepancy

Detected mismatches between entered data and documents.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| request | ForeignKey | Parent verification request |
| field_name | CharField | Name of mismatched field |
| entered_value | TextField | Value entered in system |
| document_value | TextField | Value extracted from document |
| severity | CharField | critical/major/minor/info |
| description | TextField | Details about the discrepancy |
| is_resolved | BooleanField | Whether resolved |
| resolved_by | ForeignKey | User who resolved |
| resolution_note | TextField | Resolution explanation |

#### Severity Levels
- `critical` - Must be resolved before approval
- `major` - Significant issue requiring review
- `minor` - Small discrepancy, may be acceptable
- `info` - Informational only

---

## Documents App Models

### Document

Uploaded documents for verification.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| verification_request | ForeignKey | Related verification request |
| document_type | CharField | Type of document |
| file | FileField | Uploaded file |
| original_filename | CharField | Original file name |
| is_processed | BooleanField | OCR processing status |
| processing_error | TextField | Error if processing failed |
| page_count | IntegerField | Number of pages |
| file_size | IntegerField | File size in bytes |

#### Document Types
- `national_id` - National ID card
- `passport` - International passport
- `drivers_license` - Driver's license
- `utility_bill` - Utility bill for address verification
- `bank_statement` - Bank statement
- `application_form` - Account opening form
- `other` - Other supporting documents

### DocumentExtraction

Extracted data from documents.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| document | ForeignKey | Source document |
| raw_text | TextField | Full extracted text |
| structured_data | JSONField | Parsed field values |
| confidence_scores | JSONField | Per-field confidence |
| extraction_method | CharField | ocr/ai/manual |
| processing_time | FloatField | Time taken in seconds |

---

## Compliance App Models

### Policy

Institutional policies for compliance checking.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| name | CharField | Policy name |
| category | CharField | kyc/aml/institutional |
| description | TextField | Policy description |
| content | TextField | Full policy text |
| version | CharField | Policy version |
| effective_date | DateField | When policy takes effect |
| is_active | BooleanField | Whether policy is enforced |

### ComplianceRule

Specific rules derived from policies.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| policy | ForeignKey | Parent policy |
| name | CharField | Rule name |
| rule_type | CharField | required_document/field_validation/threshold |
| condition | JSONField | Rule condition definition |
| weight | DecimalField | Importance weight |
| is_blocking | BooleanField | Whether failure blocks approval |

### ComplianceCheck

Results of compliance rule evaluations.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| verification_request | ForeignKey | Related request |
| rule | ForeignKey | Rule that was evaluated |
| passed | BooleanField | Whether check passed |
| score | DecimalField | Compliance score |
| details | JSONField | Evaluation details |
| checked_at | DateTimeField | When check was performed |

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                           User                                   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ requested_by
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    VerificationRequest                           │
│  (customer_id, customer_data, status, overall_score, etc.)      │
└─────────────────────────────────────────────────────────────────┘
           │                    │                       │
           │                    │                       │
           ▼                    ▼                       ▼
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│    Document       │  │VerificationResult │  │   Discrepancy     │
│ (file, doc_type)  │  │ (check, score)    │  │ (field mismatch)  │
└───────────────────┘  └───────────────────┘  └───────────────────┘
           │
           ▼
┌───────────────────┐
│DocumentExtraction │
│ (raw_text, data)  │
└───────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                          Policy                                  │
│            (name, content, category, version)                   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ComplianceRule                              │
│              (condition, weight, is_blocking)                   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ComplianceCheck                              │
│           (linked to VerificationRequest + Rule)                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Indexes & Constraints

### VerificationRequest
- Index on `(customer_id, status)` for quick customer lookups
- Index on `(status, priority)` for queue management
- Index on `created_at` for time-based queries

### Document
- Index on `(verification_request_id, document_type)`
- Foreign key constraint to VerificationRequest

### Discrepancy
- Index on `(request_id, severity)` for severity filtering
- Index on `is_resolved` for pending resolution queries
