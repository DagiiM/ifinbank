"""Core utilities for iFin Bank."""
from difflib import SequenceMatcher
from typing import Any, Dict, Optional
import re


def calculate_similarity(str1: str, str2: str) -> float:
    """
    Calculate string similarity using SequenceMatcher.
    Returns a value between 0.0 and 1.0.
    """
    if not str1 or not str2:
        return 0.0
    return SequenceMatcher(None, str1.lower().strip(), str2.lower().strip()).ratio()


def normalize_name(name: str) -> str:
    """
    Normalize a name for comparison.
    - Removes extra whitespace
    - Converts to lowercase
    - Removes special characters
    """
    if not name:
        return ""
    # Remove special characters except spaces
    normalized = re.sub(r'[^\w\s]', '', name)
    # Normalize whitespace
    normalized = ' '.join(normalized.split())
    return normalized.lower()


def normalize_id_number(id_number: str) -> str:
    """
    Normalize an ID number for comparison.
    - Removes all non-alphanumeric characters
    - Converts to uppercase
    """
    if not id_number:
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', id_number).upper()


def normalize_phone(phone: str) -> str:
    """
    Normalize a phone number for comparison.
    - Removes all non-numeric characters
    - Standardizes country code format
    """
    if not phone:
        return ""
    # Remove all non-numeric characters
    digits = re.sub(r'[^\d]', '', phone)
    # Handle common Kenyan formats
    if digits.startswith('254'):
        return digits
    elif digits.startswith('0'):
        return '254' + digits[1:]
    elif digits.startswith('7') or digits.startswith('1'):
        return '254' + digits
    return digits


def format_score(score: float) -> str:
    """Format a score as a percentage string."""
    return f"{score:.1f}%"


def get_severity_for_score(score: float) -> str:
    """
    Determine severity level based on match score.
    """
    if score >= 0.95:
        return 'info'
    elif score >= 0.85:
        return 'minor'
    elif score >= 0.70:
        return 'major'
    else:
        return 'critical'


def deep_get(obj: Dict[str, Any], path: str, default: Any = None) -> Any:
    """
    Safely get a nested value from a dictionary using dot notation.
    Example: deep_get({'a': {'b': 1}}, 'a.b') returns 1
    """
    keys = path.split('.')
    current = obj
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        else:
            return default
    return current


def mask_sensitive_data(value: str, visible_chars: int = 4) -> str:
    """
    Mask sensitive data, showing only the last few characters.
    Example: mask_sensitive_data("12345678") returns "****5678"
    """
    if not value or len(value) <= visible_chars:
        return value
    masked_length = len(value) - visible_chars
    return '*' * masked_length + value[-visible_chars:]
