"""
Advanced field comparison algorithms for verification.

This module provides sophisticated comparison logic for different
data types used in identity verification, including:
- Fuzzy name matching with phonetic algorithms
- Intelligent date parsing and comparison
- ID number validation and normalization
- Address matching with component analysis
"""
import re
import logging
from typing import Dict, Any, Tuple, List, Optional
from dataclasses import dataclass
from difflib import SequenceMatcher
from datetime import datetime, date

logger = logging.getLogger(__name__)


@dataclass
class ComparisonResult:
    """Result of a field comparison."""
    field_name: str
    entered_value: str
    extracted_value: str
    similarity_score: float
    is_match: bool
    confidence: float
    comparison_method: str
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


class AdvancedComparator:
    """
    Advanced field comparison with multiple matching strategies.
    
    This class provides field-specific comparison algorithms that
    account for common OCR errors, formatting differences, and
    variations in how data is represented.
    """
    
    # Threshold configurations
    THRESHOLDS = {
        'name': {'match': 0.85, 'probable': 0.70},
        'id_number': {'match': 1.0, 'probable': 0.95},  # IDs need exact match
        'date': {'match': 1.0, 'probable': 1.0},
        'phone': {'match': 0.95, 'probable': 0.85},
        'email': {'match': 1.0, 'probable': 1.0},
        'address': {'match': 0.75, 'probable': 0.60},
    }
    
    # Common OCR error mappings
    OCR_CORRECTIONS = {
        'O': '0', '0': 'O',  # O/0 confusion
        'I': '1', '1': 'I',  # I/1 confusion
        'l': '1', '1': 'l',  # l/1 confusion
        'S': '5', '5': 'S',  # S/5 confusion
        'B': '8', '8': 'B',  # B/8 confusion
        'Z': '2', '2': 'Z',  # Z/2 confusion
        'G': '6', '6': 'G',  # G/6 confusion
    }
    
    def compare(
        self,
        field_name: str,
        entered: Any,
        extracted: Any,
        field_type: str = 'text'
    ) -> ComparisonResult:
        """
        Compare two field values with type-appropriate logic.
        
        Args:
            field_name: Name of the field being compared
            entered: Value from the application/system
            extracted: Value extracted from document
            field_type: Type hint ('name', 'date', 'id', 'phone', 'address', 'text')
            
        Returns:
            ComparisonResult with similarity score and match status
        """
        # Normalize inputs to strings
        entered_str = self._to_string(entered)
        extracted_str = self._to_string(extracted)
        
        # Handle empty values
        if not entered_str or not extracted_str:
            return ComparisonResult(
                field_name=field_name,
                entered_value=entered_str,
                extracted_value=extracted_str,
                similarity_score=0.0 if (entered_str or extracted_str) else 1.0,
                is_match=not (entered_str or extracted_str),
                confidence=0.5,
                comparison_method='empty_check',
            )
        
        # Dispatch to type-specific comparator
        comparators = {
            'name': self._compare_names,
            'date': self._compare_dates,
            'id': self._compare_id_numbers,
            'phone': self._compare_phones,
            'email': self._compare_emails,
            'address': self._compare_addresses,
            'text': self._compare_text,
        }
        
        comparator = comparators.get(field_type, self._compare_text)
        return comparator(field_name, entered_str, extracted_str)
    
    def _compare_names(
        self,
        field_name: str,
        entered: str,
        extracted: str
    ) -> ComparisonResult:
        """
        Compare names using multiple strategies.
        
        Strategies:
        1. Exact match (normalized)
        2. Token-based matching (handles reordering)
        3. Fuzzy string matching
        4. Phonetic matching (Soundex/Metaphone)
        """
        # Normalize names
        entered_norm = self._normalize_name(entered)
        extracted_norm = self._normalize_name(extracted)
        
        scores = {}
        
        # Exact normalized match
        if entered_norm == extracted_norm:
            return ComparisonResult(
                field_name=field_name,
                entered_value=entered,
                extracted_value=extracted,
                similarity_score=1.0,
                is_match=True,
                confidence=1.0,
                comparison_method='exact_normalized',
            )
        
        # Token-based comparison (handles name order variations)
        entered_tokens = set(entered_norm.split())
        extracted_tokens = set(extracted_norm.split())
        
        if entered_tokens and extracted_tokens:
            common_tokens = entered_tokens & extracted_tokens
            all_tokens = entered_tokens | extracted_tokens
            token_score = len(common_tokens) / len(all_tokens)
            scores['token'] = token_score
        
        # Fuzzy matching with SequenceMatcher
        fuzzy_score = SequenceMatcher(None, entered_norm, extracted_norm).ratio()
        scores['fuzzy'] = fuzzy_score
        
        # Phonetic matching (simplified Soundex-like)
        entered_phonetic = self._get_phonetic(entered_norm)
        extracted_phonetic = self._get_phonetic(extracted_norm)
        phonetic_score = 1.0 if entered_phonetic == extracted_phonetic else 0.0
        scores['phonetic'] = phonetic_score
        
        # Weighted combination
        final_score = (
            scores.get('token', 0) * 0.4 +
            scores.get('fuzzy', 0) * 0.4 +
            scores.get('phonetic', 0) * 0.2
        )
        
        threshold = self.THRESHOLDS['name']
        is_match = final_score >= threshold['match']
        
        return ComparisonResult(
            field_name=field_name,
            entered_value=entered,
            extracted_value=extracted,
            similarity_score=final_score,
            is_match=is_match,
            confidence=min(final_score + 0.1, 1.0),
            comparison_method='multi_strategy_name',
            details=scores,
        )
    
    def _compare_dates(
        self,
        field_name: str,
        entered: str,
        extracted: str
    ) -> ComparisonResult:
        """
        Compare dates with format-agnostic parsing.
        """
        entered_date = self._parse_date(entered)
        extracted_date = self._parse_date(extracted)
        
        if entered_date is None or extracted_date is None:
            # Fall back to string comparison
            return self._compare_text(field_name, entered, extracted)
        
        is_match = entered_date == extracted_date
        
        # Calculate how close dates are if not exact match
        if not is_match:
            days_diff = abs((entered_date - extracted_date).days)
            # Score based on day difference
            if days_diff <= 1:
                score = 0.95  # Off by 1 day - likely format issue
            elif days_diff <= 30:
                score = 0.7
            elif days_diff <= 365:
                score = 0.3
            else:
                score = 0.0
        else:
            score = 1.0
        
        return ComparisonResult(
            field_name=field_name,
            entered_value=entered,
            extracted_value=extracted,
            similarity_score=score,
            is_match=is_match,
            confidence=1.0 if (entered_date and extracted_date) else 0.5,
            comparison_method='date_parse',
            details={
                'entered_parsed': str(entered_date) if entered_date else None,
                'extracted_parsed': str(extracted_date) if extracted_date else None,
            },
        )
    
    def _compare_id_numbers(
        self,
        field_name: str,
        entered: str,
        extracted: str
    ) -> ComparisonResult:
        """
        Compare ID numbers with OCR error tolerance.
        """
        # Normalize: remove spaces and special characters
        entered_norm = re.sub(r'[^A-Z0-9]', '', entered.upper())
        extracted_norm = re.sub(r'[^A-Z0-9]', '', extracted.upper())
        
        # Exact match
        if entered_norm == extracted_norm:
            return ComparisonResult(
                field_name=field_name,
                entered_value=entered,
                extracted_value=extracted,
                similarity_score=1.0,
                is_match=True,
                confidence=1.0,
                comparison_method='exact_id',
            )
        
        # Check with OCR correction tolerance
        ocr_corrected_score = self._calculate_ocr_tolerance_score(
            entered_norm, extracted_norm
        )
        
        # Standard similarity
        similarity = SequenceMatcher(None, entered_norm, extracted_norm).ratio()
        
        # Use higher of the two scores
        final_score = max(ocr_corrected_score, similarity)
        
        # IDs need very high match
        is_match = final_score >= 0.95
        
        return ComparisonResult(
            field_name=field_name,
            entered_value=entered,
            extracted_value=extracted,
            similarity_score=final_score,
            is_match=is_match,
            confidence=0.9 if final_score > 0.9 else 0.6,
            comparison_method='id_with_ocr_tolerance',
            details={
                'normalized_entered': entered_norm,
                'normalized_extracted': extracted_norm,
                'ocr_tolerance_score': ocr_corrected_score,
            },
        )
    
    def _compare_phones(
        self,
        field_name: str,
        entered: str,
        extracted: str
    ) -> ComparisonResult:
        """
        Compare phone numbers with format normalization.
        """
        # Extract only digits
        entered_digits = re.sub(r'[^\d]', '', entered)
        extracted_digits = re.sub(r'[^\d]', '', extracted)
        
        # Remove country code prefixes for comparison
        entered_base = self._normalize_phone(entered_digits)
        extracted_base = self._normalize_phone(extracted_digits)
        
        # Exact match after normalization
        if entered_base == extracted_base:
            return ComparisonResult(
                field_name=field_name,
                entered_value=entered,
                extracted_value=extracted,
                similarity_score=1.0,
                is_match=True,
                confidence=1.0,
                comparison_method='phone_normalized',
            )
        
        # Check if one is suffix of the other (partial number entry)
        if entered_base.endswith(extracted_base) or extracted_base.endswith(entered_base):
            score = len(min(entered_base, extracted_base, key=len)) / len(max(entered_base, extracted_base, key=len))
        else:
            score = SequenceMatcher(None, entered_base, extracted_base).ratio()
        
        return ComparisonResult(
            field_name=field_name,
            entered_value=entered,
            extracted_value=extracted,
            similarity_score=score,
            is_match=score >= 0.95,
            confidence=0.85,
            comparison_method='phone_normalized',
            details={
                'normalized_entered': entered_base,
                'normalized_extracted': extracted_base,
            },
        )
    
    def _compare_emails(
        self,
        field_name: str,
        entered: str,
        extracted: str
    ) -> ComparisonResult:
        """
        Compare email addresses (case-insensitive).
        """
        entered_lower = entered.lower().strip()
        extracted_lower = extracted.lower().strip()
        
        is_match = entered_lower == extracted_lower
        
        if is_match:
            score = 1.0
        else:
            # Compare username and domain separately
            entered_parts = entered_lower.split('@')
            extracted_parts = extracted_lower.split('@')
            
            if len(entered_parts) == 2 and len(extracted_parts) == 2:
                username_score = SequenceMatcher(
                    None, entered_parts[0], extracted_parts[0]
                ).ratio()
                domain_score = 1.0 if entered_parts[1] == extracted_parts[1] else 0.0
                score = username_score * 0.7 + domain_score * 0.3
            else:
                score = SequenceMatcher(None, entered_lower, extracted_lower).ratio()
        
        return ComparisonResult(
            field_name=field_name,
            entered_value=entered,
            extracted_value=extracted,
            similarity_score=score,
            is_match=is_match,
            confidence=0.95,
            comparison_method='email_normalized',
        )
    
    def _compare_addresses(
        self,
        field_name: str,
        entered: str,
        extracted: str
    ) -> ComparisonResult:
        """
        Compare addresses with component analysis.
        """
        # Normalize addresses
        entered_norm = self._normalize_address(entered)
        extracted_norm = self._normalize_address(extracted)
        
        # Token-based comparison
        entered_tokens = set(entered_norm.split())
        extracted_tokens = set(extracted_norm.split())
        
        if not entered_tokens or not extracted_tokens:
            return self._compare_text(field_name, entered, extracted)
        
        common = entered_tokens & extracted_tokens
        total = entered_tokens | extracted_tokens
        
        token_score = len(common) / len(total)
        
        # Also do fuzzy comparison
        fuzzy_score = SequenceMatcher(None, entered_norm, extracted_norm).ratio()
        
        # Weighted combination
        final_score = token_score * 0.6 + fuzzy_score * 0.4
        
        threshold = self.THRESHOLDS['address']
        is_match = final_score >= threshold['match']
        
        return ComparisonResult(
            field_name=field_name,
            entered_value=entered,
            extracted_value=extracted,
            similarity_score=final_score,
            is_match=is_match,
            confidence=0.75,
            comparison_method='address_component',
            details={
                'common_components': list(common),
                'token_score': token_score,
                'fuzzy_score': fuzzy_score,
            },
        )
    
    def _compare_text(
        self,
        field_name: str,
        entered: str,
        extracted: str
    ) -> ComparisonResult:
        """
        Generic text comparison using fuzzy matching.
        """
        entered_norm = entered.lower().strip()
        extracted_norm = extracted.lower().strip()
        
        score = SequenceMatcher(None, entered_norm, extracted_norm).ratio()
        
        return ComparisonResult(
            field_name=field_name,
            entered_value=entered,
            extracted_value=extracted,
            similarity_score=score,
            is_match=score >= 0.85,
            confidence=0.7,
            comparison_method='fuzzy_text',
        )
    
    def _normalize_name(self, name: str) -> str:
        """Normalize a name for comparison."""
        # Remove punctuation first
        name = re.sub(r'[^\w\s]', '', name)
        # Uppercase and remove extra whitespace
        normalized = ' '.join(name.upper().split())
        # Remove common titles/prefixes
        titles = ['MR', 'MRS', 'MS', 'MISS', 'DR', 'PROF', 'SIR', 'MADAM']
        words = normalized.split()
        words = [w for w in words if w not in titles]
        return ' '.join(words)
    
    def _normalize_address(self, address: str) -> str:
        """Normalize an address for comparison."""
        normalized = address.upper()
        # Expand common abbreviations
        abbrevs = {
            'ST': 'STREET', 'RD': 'ROAD', 'AVE': 'AVENUE',
            'DR': 'DRIVE', 'LN': 'LANE', 'CT': 'COURT',
            'APT': 'APARTMENT', 'STE': 'SUITE',
            'BLDG': 'BUILDING', 'FL': 'FLOOR',
        }
        words = normalized.split()
        words = [abbrevs.get(w, w) for w in words]
        # Remove punctuation
        normalized = ' '.join(words)
        normalized = re.sub(r'[^\w\s]', '', normalized)
        return normalized
    
    def _normalize_phone(self, digits: str) -> str:
        """Normalize phone number digits."""
        # Remove leading country codes
        if digits.startswith('254'):  # Kenya
            digits = digits[3:]
        elif digits.startswith('1') and len(digits) == 11:  # USA/Canada
            digits = digits[1:]
        elif digits.startswith('44') and len(digits) > 10:  # UK
            digits = digits[2:]
        
        # Remove leading zero
        if digits.startswith('0'):
            digits = digits[1:]
        
        return digits
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string into date object."""
        formats = [
            '%Y-%m-%d', '%d-%m-%Y', '%m-%d-%Y',
            '%Y/%m/%d', '%d/%m/%Y', '%m/%d/%Y',
            '%d.%m.%Y', '%Y.%m.%d',
            '%d %b %Y', '%d %B %Y',
            '%b %d, %Y', '%B %d, %Y',
            '%Y%m%d',
        ]
        
        date_str = date_str.strip()
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None
    
    def _get_phonetic(self, text: str) -> str:
        """
        Generate a simple phonetic key for a string.
        
        This is a simplified Soundex-like algorithm.
        """
        if not text:
            return ''
        
        text = text.upper()
        
        # Keep first letter
        key = text[0]
        
        # Mapping of letters to phonetic codes
        mapping = {
            'B': '1', 'F': '1', 'P': '1', 'V': '1',
            'C': '2', 'G': '2', 'J': '2', 'K': '2', 'Q': '2', 'S': '2', 'X': '2', 'Z': '2',
            'D': '3', 'T': '3',
            'L': '4',
            'M': '5', 'N': '5',
            'R': '6',
        }
        
        prev_code = mapping.get(text[0], '0')
        
        for char in text[1:]:
            code = mapping.get(char, '0')
            if code != '0' and code != prev_code:
                key += code
                if len(key) >= 4:
                    break
            prev_code = code
        
        return key.ljust(4, '0')[:4]
    
    def _calculate_ocr_tolerance_score(
        self,
        entered: str,
        extracted: str
    ) -> float:
        """
        Calculate similarity score allowing for common OCR errors.
        """
        if len(entered) != len(extracted):
            return 0.0
        
        matches = 0
        for e, x in zip(entered, extracted):
            if e == x:
                matches += 1
            elif self.OCR_CORRECTIONS.get(e) == x or self.OCR_CORRECTIONS.get(x) == e:
                matches += 0.8  # Partial credit for OCR-correctable errors
        
        return matches / len(entered)
    
    def _to_string(self, value: Any) -> str:
        """Convert any value to string."""
        if value is None:
            return ''
        return str(value).strip()


class BatchComparator:
    """
    Batch comparison of multiple fields with aggregated results.
    """
    
    # Field to comparison type mapping
    FIELD_TYPES = {
        'full_name': 'name',
        'name': 'name',
        'first_name': 'name',
        'last_name': 'name',
        'surname': 'name',
        'given_name': 'name',
        
        'date_of_birth': 'date',
        'dob': 'date',
        'birth_date': 'date',
        'issue_date': 'date',
        'expiry_date': 'date',
        
        'id_number': 'id',
        'national_id': 'id',
        'passport_number': 'id',
        'license_number': 'id',
        
        'phone': 'phone',
        'mobile': 'phone',
        'telephone': 'phone',
        
        'email': 'email',
        'email_address': 'email',
        
        'address': 'address',
        'residential_address': 'address',
        'postal_address': 'address',
    }
    
    def __init__(self):
        self.comparator = AdvancedComparator()
    
    def compare_all(
        self,
        entered_data: Dict[str, Any],
        extracted_data: Dict[str, Any],
        fields: List[str] = None
    ) -> Dict[str, ComparisonResult]:
        """
        Compare all matching fields between two datasets.
        
        Args:
            entered_data: Data from application/system
            extracted_data: Data extracted from documents
            fields: Optional list of fields to compare (compares all if None)
            
        Returns:
            Dict mapping field names to ComparisonResults
        """
        results = {}
        
        # Determine fields to compare
        if fields is None:
            fields = set(entered_data.keys()) & set(extracted_data.keys())
        
        for field in fields:
            if field not in entered_data or field not in extracted_data:
                continue
            
            field_type = self.FIELD_TYPES.get(field.lower(), 'text')
            
            results[field] = self.comparator.compare(
                field_name=field,
                entered=entered_data[field],
                extracted=extracted_data[field],
                field_type=field_type,
            )
        
        return results
    
    def calculate_overall_score(
        self,
        results: Dict[str, ComparisonResult],
        weights: Dict[str, float] = None
    ) -> Tuple[float, float]:
        """
        Calculate overall verification score from comparison results.
        
        Args:
            results: Dict of ComparisonResults
            weights: Optional field weights (equal weights if None)
            
        Returns:
            Tuple of (overall_score, confidence)
        """
        if not results:
            return 0.0, 0.0
        
        if weights is None:
            # Default weights
            weights = {
                'id_number': 2.0,
                'full_name': 1.5,
                'date_of_birth': 1.5,
            }
        
        total_weight = 0.0
        weighted_score = 0.0
        weighted_confidence = 0.0
        
        for field, result in results.items():
            weight = weights.get(field, 1.0)
            total_weight += weight
            weighted_score += result.similarity_score * weight
            weighted_confidence += result.confidence * weight
        
        overall_score = weighted_score / total_weight if total_weight > 0 else 0.0
        overall_confidence = weighted_confidence / total_weight if total_weight > 0 else 0.0
        
        return overall_score, overall_confidence
