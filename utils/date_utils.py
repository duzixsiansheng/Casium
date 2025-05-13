from datetime import datetime
from typing import Optional

def standardize_date(date_str: str) -> Optional[str]:
    """
    Standardize date to MM/DD/YYYY format
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        Standardized date string or None if parsing fails
    """
    if not date_str or date_str.lower() in ["none", "null", "n/a"]:
        return None
    
    # Common date formats to try
    date_formats = [
        "%m/%d/%Y",    # MM/DD/YYYY
        "%d/%m/%Y",    # DD/MM/YYYY
        "%Y-%m-%d",    # YYYY-MM-DD
        "%m-%d-%Y",    # MM-DD-YYYY
        "%d-%m-%Y",    # DD-MM-YYYY
        "%B %d, %Y",   # Month DD, YYYY
        "%d %B %Y",    # DD Month YYYY
        "%Y/%m/%d",    # YYYY/MM/DD
        "%m/%d/%y",    # MM/DD/YY
        "%d/%m/%y",    # DD/MM/YY
        "%m-%d-%y",    # MM-DD-YY
        "%d-%m-%y",    # DD-MM-YY
    ]
    
    # Clean the date string
    date_str = date_str.strip()
    
    for fmt in date_formats:
        try:
            date_obj = datetime.strptime(date_str, fmt)
            return date_obj.strftime("%m/%d/%Y")
        except ValueError:
            continue
    
    # If no format matches, return the original
    return date_str

def parse_date_components(date_str: str) -> Optional[dict]:
    """
    Parse date into components (month, day, year)
    
    Args:
        date_str: Date string
        
    Returns:
        Dictionary with month, day, year or None
    """
    standardized = standardize_date(date_str)
    
    if standardized and "/" in standardized:
        parts = standardized.split("/")
        if len(parts) == 3:
            return {
                "month": int(parts[0]),
                "day": int(parts[1]),
                "year": int(parts[2])
            }
    
    return None

def is_date_valid(date_str: str) -> bool:
    """
    Check if a date string is valid
    
    Args:
        date_str: Date string to validate
        
    Returns:
        True if date is valid
    """
    try:
        standardized = standardize_date(date_str)
        if standardized:
            # Check if it's a valid date
            datetime.strptime(standardized, "%m/%d/%Y")
            return True
    except:
        pass
    
    return False