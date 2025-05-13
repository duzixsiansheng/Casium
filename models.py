from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel

# Document types enumeration
class DocumentType(str, Enum):
    PASSPORT = "passport"
    DRIVER_LICENSE = "driver_license"
    EAD_CARD = "ead_card"
    UNKNOWN = "unknown"

# Field definitions for each document type
DOCUMENT_FIELDS = {
    DocumentType.PASSPORT: {
        "full_name": str,
        "date_of_birth": str,
        "country": str,
        "issue_date": str,
        "expiration_date": str,
        "passport_number": str
    },
    DocumentType.DRIVER_LICENSE: {
        "license_number": str,
        "date_of_birth": str,
        "issue_date": str,
        "expiration_date": str,
        "first_name": str,
        "last_name": str,
        "address": str
    },
    DocumentType.EAD_CARD: {
        "card_number": str,
        "category": str,
        "card_expires_date": str,
        "last_name": str,
        "first_name": str,
        "date_of_birth": str
    }
}

# Response models
class ClassificationResponse(BaseModel):
    document_type: DocumentType

class FieldExtractionResponse(BaseModel):
    document_type: DocumentType
    document_content: Dict[str, Any]
    confidence_scores: Optional[Dict[str, float]] = None

# Request models
class ProcessingOptions(BaseModel):
    extract_fields: bool = True
    standardize_dates: bool = True
    split_names: bool = True