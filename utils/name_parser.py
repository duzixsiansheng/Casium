"""Name parsing utilities for handling various name formats"""

import re
from typing import Tuple, Optional, List

class NameParser:
    """Intelligent name parsing with various strategies"""
    
    # Common name prefixes and suffixes
    PREFIXES = {
        'mr', 'mrs', 'ms', 'miss', 'dr', 'prof', 'sir', 'dame', 'rev', 'fr',
        'mr.', 'mrs.', 'ms.', 'dr.', 'prof.'
    }
    
    SUFFIXES = {
        'jr', 'sr', 'ii', 'iii', 'iv', 'v', 'phd', 'md', 'esq', 'dds',
        'jr.', 'sr.', 'ph.d.', 'm.d.', 'esq.', 'd.d.s.'
    }
    
    # Common compound last name indicators
    COMPOUND_INDICATORS = {
        'de', 'da', 'di', 'del', 'della', 'van', 'von', 'der', 'den', 'la', 'le',
        'mac', 'mc', 'o', "o'", 'san', 'santa', 'st', 'st.'
    }
    
    # Cultural name patterns
    ASIAN_SURNAMES = {
        # Common Chinese surnames
        'wang', 'li', 'zhang', 'liu', 'chen', 'yang', 'huang', 'zhao', 'wu', 'zhou',
        'xu', 'sun', 'ma', 'zhu', 'hu', 'lin', 'guo', 'he', 'luo', 'gao',
        # Common Korean surnames
        'kim', 'lee', 'park', 'choi', 'jung', 'kang', 'cho', 'yoon', 'jang', 'lim',
        # Common Japanese surnames
        'sato', 'suzuki', 'takahashi', 'tanaka', 'watanabe', 'ito', 'yamamoto',
        'nakamura', 'kobayashi', 'kato', 'yoshida', 'yamada', 'sasaki'
    }
    
    @staticmethod
    def parse_name(full_name: str, cultural_hint: Optional[str] = None) -> Tuple[str, str]:
        """
        Parse a full name into first and last name components
        
        Args:
            full_name: The complete name string
            cultural_hint: Optional hint about cultural origin (e.g., 'asian', 'hispanic')
        
        Returns:
            Tuple of (first_name, last_name)
        """
        if not full_name or not full_name.strip():
            return "", ""
        
        # Clean and normalize the name
        full_name = full_name.strip()
        
        # Handle special cases
        if ',' in full_name:
            # Format: "Last, First" or "Last, First Middle"
            parts = full_name.split(',', 1)
            last_name = parts[0].strip()
            first_name = parts[1].strip()
            # If there are multiple words after comma, take the first as first name
            if ' ' in first_name:
                first_name = first_name.split()[0]
            return first_name, last_name
        
        # Split into words
        words = full_name.split()
        
        if len(words) == 0:
            return "", ""
        
        if len(words) == 1:
            # Single word - assume it's the first name
            return words[0], ""
        
        if len(words) == 2:
            # Two words - apply cultural patterns if available
            if cultural_hint == 'asian' or NameParser._is_asian_name_pattern(words):
                # Asian names often have surname first
                return words[1], words[0]
            else:
                # Western pattern: first last
                return words[0], words[1]
        
        # Three or more words - more complex parsing
        return NameParser._parse_complex_name(words, cultural_hint)
    
    @staticmethod
    def _parse_complex_name(words: List[str], cultural_hint: Optional[str] = None) -> Tuple[str, str]:
        """Parse names with three or more words"""
        
        # Remove prefixes
        start_idx = 0
        if words[0].lower() in NameParser.PREFIXES:
            start_idx = 1
        
        # Remove suffixes
        end_idx = len(words)
        if words[-1].lower() in NameParser.SUFFIXES:
            end_idx -= 1
        
        # Get the core name parts
        core_words = words[start_idx:end_idx]
        
        if len(core_words) <= 1:
            # After removing prefixes/suffixes, only one word left
            return core_words[0] if core_words else "", ""
        
        # Check for compound last names
        compound_start = NameParser._find_compound_start(core_words)
        
        if compound_start > 0:
            # Found compound last name
            first_name = ' '.join(core_words[:compound_start])
            last_name = ' '.join(core_words[compound_start:])
            return first_name, last_name
        
        # Check for Asian pattern (family name first)
        if cultural_hint == 'asian' or NameParser._is_asian_name_pattern(core_words):
            return ' '.join(core_words[1:]), core_words[0]
        
        # Default pattern: last word is surname, rest is first name
        # This handles cases like "Mary Jane Smith" -> first: "Mary Jane", last: "Smith"
        if len(core_words) > 2:
            return ' '.join(core_words[:-1]), core_words[-1]
        else:
            return core_words[0], core_words[1]
    
    @staticmethod
    def _find_compound_start(words: List[str]) -> int:
        """Find where a compound last name starts"""
        for i, word in enumerate(words[:-1]):  # Don't check the last word
            if word.lower() in NameParser.COMPOUND_INDICATORS:
                return i
        return -1
    
    @staticmethod
    def _is_asian_name_pattern(words: List[str]) -> bool:
        """Detect if the name follows Asian naming conventions"""
        if not words:
            return False
        
        # Check if first word is a known Asian surname
        first_word = words[0].lower()
        if first_word in NameParser.ASIAN_SURNAMES:
            return True
        
        # Check for typical Asian name patterns (short surnames)
        if len(words[0]) <= 3 and len(words) > 1:
            # Many Asian surnames are short (1-3 characters in romanization)
            return True
        
        return False
    
    @staticmethod
    def extract_middle_name(full_name: str) -> Tuple[str, str, str]:
        """
        Extract first, middle, and last names
        
        Returns:
            Tuple of (first_name, middle_name, last_name)
        """
        words = full_name.strip().split()
        
        if len(words) <= 2:
            first, last = NameParser.parse_name(full_name)
            return first, "", last
        
        # For three or more words, assume middle names
        # Remove prefixes and suffixes first
        start_idx = 0
        if words[0].lower() in NameParser.PREFIXES:
            start_idx = 1
        
        end_idx = len(words)
        if words[-1].lower() in NameParser.SUFFIXES:
            end_idx -= 1
        
        core_words = words[start_idx:end_idx]
        
        if len(core_words) >= 3:
            return core_words[0], ' '.join(core_words[1:-1]), core_words[-1]
        else:
            return NameParser.parse_name(full_name)[0], "", NameParser.parse_name(full_name)[1]

# Additional utility functions
def normalize_name(name: str) -> str:
    """Normalize name formatting"""
    if not name:
        return ""
    
    # Capitalize properly
    words = name.split()
    normalized = []
    
    for word in words:
        if word.lower() in NameParser.COMPOUND_INDICATORS:
            # Keep compound indicators in lowercase
            normalized.append(word.lower())
        elif "'" in word:
            # Handle names like O'Brien
            parts = word.split("'")
            normalized.append(parts[0].capitalize() + "'" + parts[1].capitalize())
        else:
            normalized.append(word.capitalize())
    
    return ' '.join(normalized)

def guess_name_order(full_name: str, country: Optional[str] = None) -> Tuple[str, str]:
    """
    Guess the order of names based on country or cultural context
    
    Args:
        full_name: The complete name
        country: Optional country code or name
    
    Returns:
        Tuple of (first_name, last_name)
    """
    cultural_hint = None
    
    if country:
        country_lower = country.lower()
        # Map countries to cultural patterns
        asian_countries = {
            'china', 'cn', 'japan', 'jp', 'korea', 'kr', 'south korea',
            'vietnam', 'vn', 'taiwan', 'tw', 'singapore', 'sg'
        }
        
        hispanic_countries = {
            'spain', 'es', 'mexico', 'mx', 'argentina', 'ar', 'colombia', 'co',
            'chile', 'cl', 'peru', 'pe', 'venezuela', 've'
        }
        
        if country_lower in asian_countries:
            cultural_hint = 'asian'
        elif country_lower in hispanic_countries:
            cultural_hint = 'hispanic'
    
    return NameParser.parse_name(full_name, cultural_hint)