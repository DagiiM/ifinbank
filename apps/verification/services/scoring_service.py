"""Scoring service for calculating verification scores."""
from typing import List, Dict
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class ScoringService:
    """
    Service for calculating verification scores.
    
    Uses weighted scoring based on check type importance.
    """
    
    # Weight factors for different check types
    DEFAULT_WEIGHTS = {
        'identity': 0.35,    # Identity verification is most important
        'document': 0.20,    # Document authenticity
        'compliance': 0.30,  # Regulatory compliance
        'policy': 0.10,      # Institutional policies
        'address': 0.05,     # Address verification
    }
    
    def __init__(self, weights: Dict[str, float] = None):
        """
        Initialize scoring service.
        
        Args:
            weights: Custom weight dictionary (optional)
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
    
    def calculate_weighted_score(self, results: List) -> float:
        """
        Calculate overall weighted score from verification results.
        
        Args:
            results: List of VerificationResult objects
            
        Returns:
            Weighted score between 0 and 100
        """
        if not results:
            return 0.0
        
        # Group results by check type
        type_scores = {}
        type_counts = {}
        
        for result in results:
            check_type = result.check_type
            score = float(result.score)
            
            if check_type not in type_scores:
                type_scores[check_type] = 0.0
                type_counts[check_type] = 0
            
            type_scores[check_type] += score
            type_counts[check_type] += 1
        
        # Calculate average score per type
        type_averages = {}
        for check_type in type_scores:
            type_averages[check_type] = type_scores[check_type] / type_counts[check_type]
        
        # Calculate weighted sum
        weighted_sum = 0.0
        total_weight = 0.0
        
        for check_type, avg_score in type_averages.items():
            weight = self.weights.get(check_type, 0.1)  # Default weight if not specified
            weighted_sum += avg_score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        final_score = weighted_sum / total_weight
        
        logger.debug(
            f"Calculated score: {final_score:.2f} from {len(results)} results, "
            f"type averages: {type_averages}"
        )
        
        return round(final_score, 2)
    
    def calculate_simple_average(self, results: List) -> float:
        """
        Calculate simple average of all result scores.
        
        Args:
            results: List of VerificationResult objects
            
        Returns:
            Average score between 0 and 100
        """
        if not results:
            return 0.0
        
        total = sum(float(r.score) for r in results)
        return round(total / len(results), 2)
    
    def get_score_breakdown(self, results: List) -> Dict:
        """
        Get detailed breakdown of scores by category.
        
        Returns:
            Dictionary with per-category scores and counts
        """
        breakdown = {}
        
        for result in results:
            check_type = result.check_type
            
            if check_type not in breakdown:
                breakdown[check_type] = {
                    'total_score': 0.0,
                    'count': 0,
                    'passed': 0,
                    'failed': 0,
                    'weight': self.weights.get(check_type, 0.1)
                }
            
            breakdown[check_type]['total_score'] += float(result.score)
            breakdown[check_type]['count'] += 1
            if result.passed:
                breakdown[check_type]['passed'] += 1
            else:
                breakdown[check_type]['failed'] += 1
        
        # Calculate averages
        for check_type in breakdown:
            count = breakdown[check_type]['count']
            if count > 0:
                breakdown[check_type]['average'] = round(
                    breakdown[check_type]['total_score'] / count, 2
                )
            else:
                breakdown[check_type]['average'] = 0.0
        
        return breakdown
    
    def get_grade(self, score: float) -> str:
        """
        Convert numeric score to letter grade.
        
        Args:
            score: Score between 0 and 100
            
        Returns:
            Letter grade (A, B, C, D, F)
        """
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'
    
    def get_recommendation(self, score: float, has_critical_issues: bool = False) -> str:
        """
        Get recommendation text based on score.
        
        Args:
            score: Score between 0 and 100
            has_critical_issues: Whether there are critical discrepancies
            
        Returns:
            Recommendation string
        """
        if has_critical_issues:
            return "REVIEW REQUIRED: Critical issues detected that need manual resolution"
        
        if score >= 85:
            return "APPROVED: All verification checks passed with high confidence"
        elif score >= 70:
            return "REVIEW RECOMMENDED: Score is acceptable but manual review advised"
        elif score >= 50:
            return "CAUTION: Several verification issues detected, thorough review required"
        else:
            return "REJECTED: Verification failed, significant discrepancies found"
