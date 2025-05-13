from datetime import datetime
from typing import Optional, List, Tuple
import re

class DateStandardizer:
    """Intelligent date standardization with country/context awareness"""
    
    # Country-specific date format preferences
    COUNTRY_DATE_FORMATS = {
        # MM/DD/YYYY countries
        'united_states': 'MM/DD/YYYY',
        'us': 'MM/DD/YYYY',
        'usa': 'MM/DD/YYYY',
        'philippines': 'MM/DD/YYYY',
        'palau': 'MM/DD/YYYY',
        'canada': 'MM/DD/YYYY',
        'micronesia': 'MM/DD/YYYY',
        
        # DD/MM/YYYY countries (most of the world)
        'united_kingdom': 'DD/MM/YYYY',
        'uk': 'DD/MM/YYYY',
        'great_britain': 'DD/MM/YYYY',
        'australia': 'DD/MM/YYYY',
        'new_zealand': 'DD/MM/YYYY',
        'india': 'DD/MM/YYYY',
        'germany': 'DD/MM/YYYY',
        'france': 'DD/MM/YYYY',
        'italy': 'DD/MM/YYYY',
        'spain': 'DD/MM/YYYY',
        'brazil': 'DD/MM/YYYY',
        'argentina': 'DD/MM/YYYY',
        'mexico': 'DD/MM/YYYY',
        'russia': 'DD/MM/YYYY',
        'south_africa': 'DD/MM/YYYY',
        'ireland': 'DD/MM/YYYY',
        'pakistan': 'DD/MM/YYYY',
        'bangladesh': 'DD/MM/YYYY',
        'nigeria': 'DD/MM/YYYY',
        'egypt': 'DD/MM/YYYY',
        'vietnam': 'DD/MM/YYYY',
        'thailand': 'DD/MM/YYYY',
        'singapore': 'DD/MM/YYYY',
        'malaysia': 'DD/MM/YYYY',
        'indonesia': 'DD/MM/YYYY',
        
        # Special formats
        'china': 'YYYY/MM/DD',
        'cn': 'YYYY/MM/DD',
        'japan': 'YYYY/MM/DD',
        'jp': 'YYYY/MM/DD',
        'korea': 'YYYY/MM/DD',
        'kr': 'YYYY/MM/DD',
        'south_korea': 'YYYY/MM/DD',
        'taiwan': 'YYYY/MM/DD',
        'tw': 'YYYY/MM/DD',
        'hungary': 'YYYY/MM/DD',
        'lithuania': 'YYYY/MM/DD',
        'sweden': 'YYYY-MM-DD',  # ISO format
        'finland': 'DD.MM.YYYY',
        'netherlands': 'DD-MM-YYYY',
    }
    
    @staticmethod
    def standardize_date(date_str: str, country: Optional[str] = None, context_clues: Optional[List[str]] = None) -> Optional[str]:
        """
        Standardize date to MM/DD/YYYY format with intelligent parsing
        
        Args:
            date_str: Date string in various formats
            country: Country code or name for format hints
            context_clues: List of other dates for pattern detection
            
        Returns:
            Standardized date string in MM/DD/YYYY format
        """
        if not date_str or date_str.lower() in ["none", "null", "n/a", ""]:
            return None
        
        # Clean the date string
        date_str = date_str.strip()
        
        # Try multiple parsing strategies
        result = None
        
        # Strategy 1: Try unambiguous formats first
        result = DateStandardizer._try_unambiguous_formats(date_str)
        if result:
            return result
        
        # Strategy 2: Try country-specific format if country is provided
        if country:
            result = DateStandardizer._try_country_format(date_str, country)
            if result:
                return result
        
        # Strategy 3: Try to detect format from the date itself
        result = DateStandardizer._try_detect_format(date_str)
        if result:
            return result
        
        # Strategy 4: Use context clues if available
        if context_clues:
            result = DateStandardizer._try_context_based_parsing(date_str, context_clues)
            if result:
                return result
        
        # Strategy 5: Fallback with common patterns
        result = DateStandardizer._try_common_formats(date_str)
        if result:
            return result
        
        # If all strategies fail, return the original string
        return date_str
    
    @staticmethod
    def _try_unambiguous_formats(date_str: str) -> Optional[str]:
        """Try parsing unambiguous date formats"""
        unambiguous_formats = [
            # Formats with month names
            ("%B %d, %Y", None),      # January 15, 2023
            ("%d %B %Y", None),       # 15 January 2023
            ("%b %d, %Y", None),      # Jan 15, 2023
            ("%d %b %Y", None),       # 15 Jan 2023
            ("%d-%b-%Y", None),       # 15-Jan-2023
            ("%d/%b/%Y", None),       # 15/Jan/2023
            
            # ISO format
            ("%Y-%m-%d", None),       # 2023-01-15
            
            # Clear formats with 4-digit year
            ("%m-%d-%Y", None),       # 01-15-2023
            ("%d-%m-%Y", None),       # 15-01-2023
            ("%Y/%m/%d", None),       # 2023/01/15
            
            # Formats with dots (common in Europe)
            ("%d.%m.%Y", None),       # 15.01.2023
        ]
        
        for fmt, _ in unambiguous_formats:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                return date_obj.strftime("%m/%d/%Y")
            except ValueError:
                continue
        
        return None
    
    @staticmethod
    def _try_country_format(date_str: str, country: str) -> Optional[str]:
        """Try parsing based on country-specific format"""
        country_lower = country.lower()
        
        # Get the expected format for this country
        expected_format = DateStandardizer.COUNTRY_DATE_FORMATS.get(country_lower)
        
        if not expected_format:
            return None
        
        # Map format patterns to strptime formats
        format_mappings = {
            'MM/DD/YYYY': ["%m/%d/%Y", "%m-%d-%Y", "%m.%d.%Y"],
            'DD/MM/YYYY': ["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"],
            'YYYY/MM/DD': ["%Y/%m/%d", "%Y-%m-%d", "%Y.%m.%d"],
            'DD.MM.YYYY': ["%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"],
            'DD-MM-YYYY': ["%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y"],
            'YYYY-MM-DD': ["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"],
        }
        
        formats_to_try = format_mappings.get(expected_format, [])
        
        for fmt in formats_to_try:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                return date_obj.strftime("%m/%d/%Y")
            except ValueError:
                continue
        
        # Also try with 2-digit years
        for fmt in formats_to_try:
            fmt_2digit = fmt.replace("%Y", "%y")
            try:
                date_obj = datetime.strptime(date_str, fmt_2digit)
                return date_obj.strftime("%m/%d/%Y")
            except ValueError:
                continue
        
        return None
    
    @staticmethod
    def _try_detect_format(date_str: str) -> Optional[str]:
        """Try to detect format from the date itself"""
        
        # Look for patterns that indicate format
        parts = re.split(r'[-/.\s]', date_str)
        
        if len(parts) == 3:
            # Check if any part is clearly a year
            year_part = None
            year_index = None
            
            for i, part in enumerate(parts):
                if len(part) == 4 and part.isdigit():
                    year_part = part
                    year_index = i
                    break
            
            if year_part:
                # We found a 4-digit year
                year = int(year_part)
                
                # Remove year from parts for further analysis
                remaining_parts = [parts[j] for j in range(3) if j != year_index]
                
                # Check which part is likely the month
                for i, part in enumerate(remaining_parts):
                    if part.isdigit():
                        value = int(part)
                        if value > 12:  # Must be day
                            day_index = i
                            month_index = 1 - i
                            try:
                                month = int(remaining_parts[month_index])
                                day = value
                                date_obj = datetime(year, month, day)
                                return date_obj.strftime("%m/%d/%Y")
                            except:
                                pass
                
                # If we can't determine, try both possibilities
                if all(part.isdigit() for part in remaining_parts):
                    val1, val2 = int(remaining_parts[0]), int(remaining_parts[1])
                    
                    # Try first as month, second as day
                    try:
                        if val1 <= 12:
                            date_obj = datetime(year, val1, val2)
                            return date_obj.strftime("%m/%d/%Y")
                    except:
                        pass
                    
                    # Try first as day, second as month
                    try:
                        if val2 <= 12:
                            date_obj = datetime(year, val2, val1)
                            return date_obj.strftime("%m/%d/%Y")
                    except:
                        pass
        
        return None
    
    @staticmethod
    def _try_context_based_parsing(date_str: str, context_clues: List[str]) -> Optional[str]:
        """Use other dates as context to determine format"""
        
        # Parse context dates to find patterns
        parsed_contexts = []
        for context_date in context_clues:
            # Try to parse each context date
            result = DateStandardizer._try_unambiguous_formats(context_date)
            if result:
                parsed_contexts.append(result)
        
        if not parsed_contexts:
            return None
        
        # Analyze the context dates to determine likely format
        # This is a simplified version - could be made more sophisticated
        parts = re.split(r'[-/.\s]', date_str)
        
        if len(parts) == 3 and all(part.isdigit() for part in parts):
            val1, val2, val3 = int(parts[0]), int(parts[1]), int(parts[2])
            
            # Try different interpretations
            possible_dates = []
            
            # MM/DD/YYYY
            try:
                if val1 <= 12:
                    date_obj = datetime(val3, val1, val2) if val3 > 31 else datetime(2000 + val3, val1, val2)
                    possible_dates.append(date_obj)
            except:
                pass
            
            # DD/MM/YYYY
            try:
                if val2 <= 12:
                    date_obj = datetime(val3, val2, val1) if val3 > 31 else datetime(2000 + val3, val2, val1)
                    possible_dates.append(date_obj)
            except:
                pass
            
            # Return the most plausible date based on context
            if possible_dates:
                return possible_dates[0].strftime("%m/%d/%Y")
        
        return None
    
    @staticmethod
    def _try_common_formats(date_str: str) -> Optional[str]:
        """Try a comprehensive list of common date formats"""
        common_formats = [
            "%m/%d/%Y", "%m/%d/%y",      # US format
            "%d/%m/%Y", "%d/%m/%y",      # European format
            "%Y-%m-%d",                  # ISO format
            "%m-%d-%Y", "%m-%d-%y",
            "%d-%m-%Y", "%d-%m-%y",
            "%m.%d.%Y", "%m.%d.%y",
            "%d.%m.%Y", "%d.%m.%y",
            "%Y/%m/%d",
            "%Y.%m.%d",
        ]
        
        for fmt in common_formats:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                return date_obj.strftime("%m/%d/%Y")
            except ValueError:
                continue
        
        return None
    
    @staticmethod
    def validate_date(date_str: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a date and return whether it's valid and any issues
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not date_str:
            return False, "Date is empty"
        
        try:
            # Check if it's in our standard format
            datetime.strptime(date_str, "%m/%d/%Y")
            return True, None
        except ValueError:
            # Try to parse it in any format
            result = DateStandardizer.standardize_date(date_str)
            if result and result != date_str:
                return True, f"Date was reformatted from '{date_str}' to '{result}'"
            else:
                return False, f"Could not parse date: '{date_str}'"

# Main function that will be used by the field extractor
def standardize_date(date_str: str, country: Optional[str] = None, context_dates: Optional[List[str]] = None) -> Optional[str]:
    """
    Standardize date to MM/DD/YYYY format
    
    Args:
        date_str: Date string in various formats
        country: Country code for format hints
        context_dates: Other dates from the same document for pattern detection
        
    Returns:
        Standardized date string or None
    """
    return DateStandardizer.standardize_date(date_str, country, context_dates)