"""
Tests for the verification services.
"""
import pytest
from decimal import Decimal
from datetime import date
from django.test import TestCase

from apps.verification.services.advanced_comparison import (
    AdvancedComparator,
    BatchComparator,
    ComparisonResult,
)


class TestAdvancedComparator(TestCase):
    """Tests for the AdvancedComparator class."""
    
    def setUp(self):
        self.comparator = AdvancedComparator()
    
    def test_exact_name_match(self):
        """Test exact name matching."""
        result = self.comparator.compare(
            field_name='full_name',
            entered='John Doe',
            extracted='John Doe',
            field_type='name',
        )
        
        self.assertTrue(result.is_match)
        self.assertAlmostEqual(result.similarity_score, 1.0)
    
    def test_case_insensitive_name_match(self):
        """Test case-insensitive name matching."""
        result = self.comparator.compare(
            field_name='full_name',
            entered='JOHN DOE',
            extracted='john doe',
            field_type='name',
        )
        
        self.assertTrue(result.is_match)
        self.assertAlmostEqual(result.similarity_score, 1.0)
    
    def test_name_with_title(self):
        """Test name matching with titles removed."""
        result = self.comparator.compare(
            field_name='full_name',
            entered='Mr. John Doe',
            extracted='John Doe',
            field_type='name',
        )
        
        self.assertTrue(result.is_match)
    
    def test_name_token_reorder(self):
        """Test name matching with reordered tokens."""
        result = self.comparator.compare(
            field_name='full_name',
            entered='John Michael Doe',
            extracted='Doe John Michael',
            field_type='name',
        )
        
        # Token reordering should give high score
        self.assertGreater(result.similarity_score, 0.7)
    
    def test_similar_names(self):
        """Test fuzzy matching for similar names."""
        result = self.comparator.compare(
            field_name='full_name',
            entered='Jon Doe',  # Typo: Jon instead of John
            extracted='John Doe',
            field_type='name',
        )
        
        # Should have high similarity but may not be exact match
        self.assertGreater(result.similarity_score, 0.7)
    
    def test_exact_id_match(self):
        """Test exact ID number matching."""
        result = self.comparator.compare(
            field_name='id_number',
            entered='12345678',
            extracted='12345678',
            field_type='id',
        )
        
        self.assertTrue(result.is_match)
        self.assertAlmostEqual(result.similarity_score, 1.0)
    
    def test_id_with_formatting(self):
        """Test ID matching ignoring formatting."""
        result = self.comparator.compare(
            field_name='id_number',
            entered='123-456-78',
            extracted='12345678',
            field_type='id',
        )
        
        self.assertTrue(result.is_match)
    
    def test_id_ocr_correction(self):
        """Test ID matching with OCR error tolerance."""
        result = self.comparator.compare(
            field_name='id_number',
            entered='12345678',
            extracted='1234567B',  # 8 -> B OCR error
            field_type='id',
        )
        
        # Should have high score due to OCR tolerance
        self.assertGreater(result.similarity_score, 0.9)
    
    def test_date_exact_match(self):
        """Test exact date matching."""
        result = self.comparator.compare(
            field_name='date_of_birth',
            entered='1990-01-15',
            extracted='1990-01-15',
            field_type='date',
        )
        
        self.assertTrue(result.is_match)
        self.assertAlmostEqual(result.similarity_score, 1.0)
    
    def test_date_format_variations(self):
        """Test date matching across different formats."""
        # YYYY-MM-DD vs DD/MM/YYYY
        result = self.comparator.compare(
            field_name='date_of_birth',
            entered='1990-01-15',
            extracted='15/01/1990',
            field_type='date',
        )
        
        self.assertTrue(result.is_match)
    
    def test_date_one_day_off(self):
        """Test date with one day difference."""
        result = self.comparator.compare(
            field_name='date_of_birth',
            entered='1990-01-15',
            extracted='1990-01-16',
            field_type='date',
        )
        
        # One day off should have high score (likely typo)
        self.assertFalse(result.is_match)
        self.assertGreater(result.similarity_score, 0.9)
    
    def test_phone_match(self):
        """Test phone number matching."""
        result = self.comparator.compare(
            field_name='phone',
            entered='+254700123456',
            extracted='0700123456',
            field_type='phone',
        )
        
        # Phone numbers should match after normalization
        self.assertGreater(result.similarity_score, 0.9)
    
    def test_email_match(self):
        """Test email matching."""
        result = self.comparator.compare(
            field_name='email',
            entered='John.Doe@email.com',
            extracted='john.doe@email.com',
            field_type='email',
        )
        
        self.assertTrue(result.is_match)
    
    def test_address_match(self):
        """Test address matching."""
        result = self.comparator.compare(
            field_name='address',
            entered='123 Main St, Nairobi',
            extracted='123 Main Street Nairobi',
            field_type='address',
        )
        
        # Abbreviation handling should give high score
        self.assertGreater(result.similarity_score, 0.7)


class TestBatchComparator(TestCase):
    """Tests for the BatchComparator class."""
    
    def setUp(self):
        self.comparator = BatchComparator()
    
    def test_compare_all_fields(self):
        """Test comparing all matching fields."""
        entered = {
            'full_name': 'John Doe',
            'id_number': '12345678',
            'date_of_birth': '1990-01-15',
        }
        
        extracted = {
            'full_name': 'JOHN DOE',
            'id_number': '12345678',
            'date_of_birth': '15/01/1990',
        }
        
        results = self.comparator.compare_all(entered, extracted)
        
        self.assertEqual(len(results), 3)
        self.assertTrue(all(r.is_match for r in results.values()))
    
    def test_calculate_overall_score(self):
        """Test overall score calculation."""
        entered = {
            'full_name': 'John Doe',
            'id_number': '12345678',
        }
        
        extracted = {
            'full_name': 'John Doe',
            'id_number': '12345678',
        }
        
        results = self.comparator.compare_all(entered, extracted)
        score, confidence = self.comparator.calculate_overall_score(results)
        
        self.assertGreater(score, 0.9)
        self.assertGreater(confidence, 0.8)
    
    def test_weighted_scoring(self):
        """Test that weights affect overall score."""
        results = {
            'id_number': ComparisonResult(
                field_name='id_number',
                entered_value='12345678',
                extracted_value='12345679',
                similarity_score=0.5,
                is_match=False,
                confidence=0.9,
                comparison_method='test',
            ),
            'full_name': ComparisonResult(
                field_name='full_name',
                entered_value='John Doe',
                extracted_value='John Doe',
                similarity_score=1.0,
                is_match=True,
                confidence=1.0,
                comparison_method='test',
            ),
        }
        
        # With default weights, id_number has weight 2.0, full_name has 1.5
        score, _ = self.comparator.calculate_overall_score(results)
        
        # Expected: (0.5 * 2.0 + 1.0 * 1.5) / 3.5 = 2.5 / 3.5 ≈ 0.714
        self.assertAlmostEqual(score, 0.714, places=2)


class TestPhoneticMatching(TestCase):
    """Tests for phonetic matching."""
    
    def setUp(self):
        self.comparator = AdvancedComparator()
    
    def test_very_similar_names(self):
        """Test very similar names with minor difference."""
        result = self.comparator.compare(
            field_name='full_name',
            entered='John Doe',
            extracted='Jon Doe',  # Missing 'h'
            field_type='name',
        )
        
        # Names with minor differences should have good similarity
        self.assertGreater(result.similarity_score, 0.6)
        # But shouldn't be exact match
        self.assertLess(result.similarity_score, 1.0)
    
    def test_completely_different_names(self):
        """Test names that are completely different."""
        result = self.comparator.compare(
            field_name='full_name',
            entered='John Smith',
            extracted='Maria Garcia',
            field_type='name',
        )
        
        # Very different names should have low score
        self.assertLess(result.similarity_score, 0.4)

