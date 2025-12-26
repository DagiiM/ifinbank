"""
Management command to seed initial compliance policies.

Usage:
    python manage.py seed_policies
"""
from datetime import date
from django.core.management.base import BaseCommand
from apps.compliance.models import Policy, ComplianceRule


class Command(BaseCommand):
    help = 'Seed initial compliance policies and rules'

    def handle(self, *args, **options):
        self.stdout.write('Seeding compliance policies...')
        
        # KYC Policy
        kyc_policy, created = Policy.objects.get_or_create(
            code='KYC-001',
            defaults={
                'name': 'Know Your Customer (KYC) Requirements',
                'category': 'kyc',
                'description': 'Standard KYC requirements for individual customer onboarding',
                'content': '''
# Know Your Customer (KYC) Requirements

## Purpose
This policy establishes the minimum requirements for customer identification and verification during account opening.

## Scope
Applies to all individual customer account openings.

## Requirements

### 1. Identity Verification
- Valid government-issued photo ID (National ID, Passport, or Driver's License)
- ID must be current (not expired)
- Photo must be clearly visible and match applicant

### 2. Required Information
- Full legal name as shown on ID
- Date of birth
- Nationality
- Residential address
- Contact information (phone and/or email)

### 3. Age Requirements
- Minimum age for account opening: 18 years
- Minors require parental/guardian consent and documentation

### 4. Address Verification
- Utility bill (less than 3 months old) OR
- Bank statement OR
- Lease agreement

### 5. Document Quality Standards
- Documents must be legible
- No alterations or tampering evident
- Color copies preferred
- Minimum resolution: 300 DPI for scanned documents

## Compliance
Failure to meet these requirements will result in:
- Application rejection OR
- Request for additional documentation OR
- Escalation to Compliance Officer
                '''.strip(),
                'effective_date': date(2024, 1, 1),
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'  Created: {kyc_policy.code}'))
            
            # Add KYC rules
            ComplianceRule.objects.create(
                policy=kyc_policy,
                code='KYC-001-R01',
                name='Valid ID Document Required',
                rule_type='required_document',
                condition={'document_types': ['national_id', 'passport', 'drivers_license']},
                is_blocking=True,
                weight=2.0,
                error_message='A valid government-issued ID document is required',
            )
            
            ComplianceRule.objects.create(
                policy=kyc_policy,
                code='KYC-001-R02',
                name='Minimum Age 18',
                rule_type='age_verification',
                condition={'min_age': 18},
                is_blocking=True,
                weight=2.0,
                error_message='Applicant must be at least 18 years old',
            )
            
            ComplianceRule.objects.create(
                policy=kyc_policy,
                code='KYC-001-R03',
                name='Required Customer Information',
                rule_type='field_validation',
                condition={'required_fields': ['full_name', 'id_number', 'date_of_birth']},
                is_blocking=True,
                weight=1.5,
                error_message='Full name, ID number, and date of birth are required',
            )
        else:
            self.stdout.write(f'  Exists: {kyc_policy.code}')
        
        # AML Policy
        aml_policy, created = Policy.objects.get_or_create(
            code='AML-001',
            defaults={
                'name': 'Anti-Money Laundering (AML) Screening',
                'category': 'aml',
                'description': 'AML screening requirements for all customers',
                'content': '''
# Anti-Money Laundering (AML) Screening Policy

## Purpose
To prevent money laundering and terrorist financing through proper customer screening.

## Requirements

### 1. Watchlist Screening
All customers must be screened against:
- OFAC Specially Designated Nationals List
- UN Security Council Sanctions List
- EU Consolidated List
- Local regulatory watchlists

### 2. PEP Identification
Identify Politically Exposed Persons (PEPs):
- Current or former senior government officials
- Senior executives of state-owned corporations
- Important political party officials
- Senior judicial officials
- Family members and close associates of PEPs

### 3. Enhanced Due Diligence
Required for:
- PEPs
- High-risk countries
- Complex ownership structures
- Unusual transaction patterns

### 4. Ongoing Monitoring
- Transaction monitoring for suspicious activity
- Periodic re-screening against updated lists
- Risk reassessment annually

## Red Flags
- Reluctance to provide information
- Inconsistent or contradictory information
- Unusual transaction requests
- Use of nominees or shell companies
                '''.strip(),
                'effective_date': date(2024, 1, 1),
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'  Created: {aml_policy.code}'))
            
            ComplianceRule.objects.create(
                policy=aml_policy,
                code='AML-001-R01',
                name='Watchlist Screening',
                rule_type='watchlist',
                condition={'lists': ['ofac', 'un', 'eu']},
                is_blocking=True,
                weight=3.0,
                error_message='Customer appears on sanctions watchlist',
            )
        else:
            self.stdout.write(f'  Exists: {aml_policy.code}')
        
        # Document Quality Policy
        doc_policy, created = Policy.objects.get_or_create(
            code='DOC-001',
            defaults={
                'name': 'Document Quality Standards',
                'category': 'institutional',
                'description': 'Standards for acceptable document quality',
                'content': '''
# Document Quality Standards

## Purpose
Ensure submitted documents meet quality standards for accurate processing.

## Image Quality Requirements
- Minimum resolution: 300 DPI
- Format: PDF, JPEG, PNG, TIFF
- Maximum file size: 10MB
- Clear, focused images without blur

## Legibility Standards
- All text must be readable
- No glare or reflections obscuring content
- Correct orientation
- Complete document visible (no cropping of edges)

## Authentication Markers
- Security features visible where applicable
- Holographic elements (if photographed) should show changes
- Watermarks visible

## Rejection Criteria
- Blurred or out-of-focus images
- Partial documents
- Heavily edited or manipulated images
- Poor lighting making text unreadable
- Overly compressed images with artifacts
                '''.strip(),
                'effective_date': date(2024, 1, 1),
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'  Created: {doc_policy.code}'))
        else:
            self.stdout.write(f'  Exists: {doc_policy.code}')
        
        # Summary
        total_policies = Policy.objects.filter(is_active=True).count()
        total_rules = ComplianceRule.objects.filter(is_active=True).count()
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Total active policies: {total_policies}'))
        self.stdout.write(self.style.SUCCESS(f'Total active rules: {total_rules}'))
        self.stdout.write('')
        self.stdout.write(self.style.NOTICE('Run "python manage.py sync_policies" to index policies in ChromaDB'))
