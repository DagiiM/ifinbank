"""Comparison service for data-to-document matching."""
from typing import List, Dict, Any, Tuple
from difflib import SequenceMatcher
import logging
import re

from apps.core.utils import (
    calculate_similarity,
    normalize_name,
    normalize_id_number,
    normalize_phone,
    get_severity_for_score
)

logger = logging.getLogger(__name__)


class ComparisonService:
    """
    Service for comparing entered customer data against extracted document data.
    
    Handles field-by-field comparison with fuzzy matching for names,
    exact matching for IDs, and normalized matching for phone numbers.
    """
    
    # Similarity thresholds
    THRESHOLD_EXACT = 0.99   # Considered exact match
    THRESHOLD_PASS = 0.85    # Pass threshold
    THRESHOLD_WARN = 0.70    # Warning threshold
    
    def __init__(self):
        """Initialize the comparison service."""
        self.field_comparators = {
            'full_name': self._compare_name,
            'first_name': self._compare_name,
            'last_name': self._compare_name,
            'id_number': self._compare_id,
            'passport_number': self._compare_id,
            'date_of_birth': self._compare_date,
            'phone': self._compare_phone,
            'email': self._compare_email,
            'address': self._compare_address,
        }
    
    def compare_all(
        self,
        customer_data: Dict[str, Any],
        documents
    ) -> Tuple[List, List]:
        """
        Compare customer data against all documents.
        
        Args:
            customer_data: Data entered in the system
            documents: QuerySet of Document objects
            
        Returns:
            Tuple of (results, discrepancies)
        """
        from ..models import VerificationResult, Discrepancy
        
        results = []
        discrepancies = []
        
        # Process each document based on type
        for document in documents:
            if not document.is_processed:
                logger.warning(f"Document {document.id} not yet processed, skipping")
                continue
            
            # Get extraction data
            extraction = document.extractions.first()
            if not extraction:
                continue
            
            extracted_data = extraction.structured_data
            
            # Determine which fields to compare based on document type
            fields_to_check = self._get_fields_for_document_type(document.document_type)
            
            for field in fields_to_check:
                entered = customer_data.get(field, '')
                extracted = extracted_data.get(field, '')
                
                if not entered and not extracted:
                    continue
                
                # Get appropriate comparator
                comparator = self.field_comparators.get(field, self._compare_generic)
                similarity, details = comparator(entered, extracted)
                
                passed = similarity >= self.THRESHOLD_PASS
                
                # Create result
                result = VerificationResult.objects.create(
                    request=document.verification_request,
                    check_type='identity',
                    check_name=f'{field}_match',
                    score=similarity * 100,
                    confidence=0.95,
                    passed=passed,
                    message=f"{field}: {similarity * 100:.0f}% match",
                    evidence={
                        'entered': entered,
                        'extracted': extracted,
                        'details': details
                    }
                )
                results.append(result)
                
                # Create discrepancy if not passing
                if not passed and entered and extracted:
                    severity = get_severity_for_score(similarity)
                    discrepancy = Discrepancy.objects.create(
                        request=document.verification_request,
                        field_name=field,
                        entered_value=str(entered),
                        document_value=str(extracted),
                        severity=severity,
                        similarity_score=similarity * 100,
                        description=f"Mismatch detected: '{entered}' vs '{extracted}' ({similarity * 100:.0f}% similar)"
                    )
                    discrepancies.append(discrepancy)
        
        return results, discrepancies
    
    def compare_identity(
        self,
        customer_data: Dict[str, Any],
        documents
    ) -> Tuple[List, List]:
        """
        Compare identity fields specifically.
        
        This is for identity document comparison (ID, passport).
        """
        id_documents = documents.filter(
            document_type__in=['national_id', 'passport', 'drivers_license']
        )
        return self.compare_all(customer_data, id_documents)
    
    def _get_fields_for_document_type(self, doc_type: str) -> List[str]:
        """Get relevant fields for a document type."""
        field_maps = {
            'national_id': ['full_name', 'id_number', 'date_of_birth'],
            'passport': ['full_name', 'passport_number', 'date_of_birth'],
            'drivers_license': ['full_name', 'date_of_birth'],
            'utility_bill': ['full_name', 'address'],
            'bank_statement': ['full_name', 'address'],
            'application_form': [
                'full_name', 'id_number', 'date_of_birth',
                'phone', 'email', 'address'
            ],
        }
        return field_maps.get(doc_type, ['full_name'])
    
    def _compare_name(self, entered: str, extracted: str) -> Tuple[float, Dict]:
        """
        Compare names with fuzzy matching.
        
        Handles:
        - Case differences (JOHN DOE vs John Doe)
        - Extra whitespace
        - Minor spelling variations
        """
        norm_entered = normalize_name(entered)
        norm_extracted = normalize_name(extracted)
        
        similarity = calculate_similarity(norm_entered, norm_extracted)
        
        # Also check if words are the same but in different order
        entered_words = set(norm_entered.split())
        extracted_words = set(norm_extracted.split())
        word_overlap = len(entered_words & extracted_words) / max(len(entered_words), len(extracted_words), 1)
        
        # Use the better of the two scores
        final_score = max(similarity, word_overlap)
        
        return final_score, {
            'normalized_entered': norm_entered,
            'normalized_extracted': norm_extracted,
            'sequence_similarity': similarity,
            'word_overlap': word_overlap
        }
    
    def _compare_id(self, entered: str, extracted: str) -> Tuple[float, Dict]:
        """
        Compare ID numbers with exact matching.
        
        Normalizes format (removes spaces, dashes) before comparing.
        """
        norm_entered = normalize_id_number(entered)
        norm_extracted = normalize_id_number(extracted)
        
        if norm_entered == norm_extracted:
            similarity = 1.0
        else:
            # Still calculate similarity for near-matches
            similarity = calculate_similarity(norm_entered, norm_extracted)
        
        return similarity, {
            'normalized_entered': norm_entered,
            'normalized_extracted': norm_extracted,
            'exact_match': norm_entered == norm_extracted
        }
    
    def _compare_date(self, entered: str, extracted: str) -> Tuple[float, Dict]:
        """
        Compare dates handling various formats.
        """
        # Normalize date formats
        def parse_date(date_str: str) -> str:
            # Remove separators and normalize
            cleaned = re.sub(r'[^\d]', '', str(date_str))
            return cleaned
        
        norm_entered = parse_date(entered)
        norm_extracted = parse_date(extracted)
        
        if norm_entered == norm_extracted:
            similarity = 1.0
        else:
            similarity = calculate_similarity(norm_entered, norm_extracted)
        
        return similarity, {
            'normalized_entered': norm_entered,
            'normalized_extracted': norm_extracted
        }
    
    def _compare_phone(self, entered: str, extracted: str) -> Tuple[float, Dict]:
        """Compare phone numbers with normalized format."""
        norm_entered = normalize_phone(entered)
        norm_extracted = normalize_phone(extracted)
        
        if norm_entered == norm_extracted:
            similarity = 1.0
        else:
            similarity = calculate_similarity(norm_entered, norm_extracted)
        
        return similarity, {
            'normalized_entered': norm_entered,
            'normalized_extracted': norm_extracted
        }
    
    def _compare_email(self, entered: str, extracted: str) -> Tuple[float, Dict]:
        """Compare email addresses (case-insensitive)."""
        norm_entered = entered.lower().strip()
        norm_extracted = extracted.lower().strip()
        
        similarity = 1.0 if norm_entered == norm_extracted else calculate_similarity(norm_entered, norm_extracted)
        
        return similarity, {}
    
    def _compare_address(self, entered: str, extracted: str) -> Tuple[float, Dict]:
        """
        Compare addresses with fuzzy matching.
        
        Addresses are tricky - lots of variations in formatting.
        """
        # Normalize common abbreviations
        def normalize_address(addr: str) -> str:
            addr = addr.lower()
            replacements = {
                'street': 'st',
                'road': 'rd',
                'avenue': 'ave',
                'drive': 'dr',
                'lane': 'ln',
                'court': 'ct',
                'apartment': 'apt',
                'number': 'no',
                'p.o. box': 'po box',
            }
            for old, new in replacements.items():
                addr = addr.replace(old, new)
            # Remove extra whitespace and punctuation
            addr = re.sub(r'[^\w\s]', ' ', addr)
            addr = ' '.join(addr.split())
            return addr
        
        norm_entered = normalize_address(entered)
        norm_extracted = normalize_address(extracted)
        
        similarity = calculate_similarity(norm_entered, norm_extracted)
        
        return similarity, {
            'normalized_entered': norm_entered,
            'normalized_extracted': norm_extracted
        }
    
    def _compare_generic(self, entered: str, extracted: str) -> Tuple[float, Dict]:
        """Generic comparison for unspecified fields."""
        return calculate_similarity(str(entered), str(extracted)), {}
