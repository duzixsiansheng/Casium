import httpx
import json
import re
from typing import Dict, Any, Optional
from models import DocumentType, DOCUMENT_FIELDS
from config import config
from utils.date_utils import standardize_date
from utils.name_parser import NameParser, guess_name_order, normalize_name

class FieldExtractor:
    """Extract fields from documents using vision LLM"""
    
    def __init__(self):
        self.api_key = config.OPENAI_API_KEY
        self.base_url = config.OPENAI_BASE_URL
        self.model = config.OPENAI_MODEL
        self.timeout = config.OPENAI_TIMEOUT
        self.temperature = config.TEMPERATURE
        self.max_tokens = config.MAX_TOKENS
    
    async def extract(self, image_base64: str, document_type: DocumentType) -> Dict[str, Any]:
        """
        Extract fields from document based on its type
        
        Args:
            image_base64: Base64 encoded image
            document_type: Type of document
            
        Returns:
            Dictionary of extracted fields
        """
        if document_type == DocumentType.UNKNOWN:
            return {}
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Get fields to extract
        fields_to_extract = DOCUMENT_FIELDS.get(document_type, {})
        
        # Create extraction prompt
        prompt = self._create_extraction_prompt(document_type, fields_to_extract)
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                if response.status_code != 200:
                    print(f"Extraction error: {response.status_code} - {response.text}")
                    return {}
                
                result = response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    
                    # Parse JSON from response
                    extracted_fields = self._parse_json_response(content)
                    
                    # Post-process fields
                    processed_fields = self._post_process_fields(
                        extracted_fields, 
                        document_type
                    )
                    
                    return processed_fields
                
                return {}
                    
            except Exception as e:
                print(f"Error during field extraction: {str(e)}")
                return {}
    
    def _create_extraction_prompt(self, document_type: DocumentType, fields: Dict) -> str:
        """Create a detailed extraction prompt"""
        field_descriptions = self._get_field_descriptions(document_type)
        
        field_list = "\n".join([
            f"- {field}: {desc}" 
            for field, desc in field_descriptions.items()
        ])
        
        example_json = json.dumps(
            {field: "value" for field in fields.keys()}, 
            indent=2
        )
        
        return f"""
        Please extract the following information from this {document_type.value.replace('_', ' ')}:
        
        {field_list}
        
        Instructions:
        1. Format the response as a JSON object with these exact field names
        2. For dates, standardize to MM/DD/YYYY format
        3. For names:
           - If the document shows first and last names separately, extract them as is
           - If only a full name is shown, extract it as "full_name"
           - If you see a name like "SMITH, JOHN" extract as first_name: "JOHN", last_name: "SMITH"
           - For Asian names (e.g., Chinese, Korean, Japanese), the family name often comes first
        4. If a field is not found or unclear, use null
        5. For country, use lowercase with underscores (e.g., "united_states")
        6. Extract exactly what you see - let post-processing handle standardization
        
        Example format:
        {example_json}
        
        Return only the JSON object, no additional text.
        """
    
    def _get_field_descriptions(self, document_type: DocumentType) -> Dict[str, str]:
        """Get human-readable descriptions for each field"""
        descriptions = {
            DocumentType.PASSPORT: {
                "full_name": "Full name of the passport holder",
                "date_of_birth": "Date of birth (MM/DD/YYYY format)",
                "country": "Issuing country (lowercase with underscores)",
                "issue_date": "Date of issue (MM/DD/YYYY format)",
                "expiration_date": "Expiration date (MM/DD/YYYY format)",
                "passport_number": "Passport number/document number"
            },
            DocumentType.DRIVER_LICENSE: {
                "license_number": "Driver's license number",
                "date_of_birth": "Date of birth (MM/DD/YYYY format)",
                "issue_date": "Issue date (MM/DD/YYYY format)",
                "expiration_date": "Expiration date (MM/DD/YYYY format)",
                "first_name": "First name only",
                "last_name": "Last name only",
                "address": "Full address"
            },
            DocumentType.EAD_CARD: {
                "card_number": "USCIS card number (with hyphens)",
                "category": "Category code (e.g., C09)",
                "card_expires_date": "Card expiration date (MM/DD/YYYY format)",
                "last_name": "Last name only",
                "first_name": "First name only",
                "date_of_birth": "Date of birth (MM/DD/YYYY format)"
            }
        }
        
        return descriptions.get(document_type, {})
    
    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Parse JSON from LLM response"""
        try:
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON object directly
                json_match = re.search(r'\{[^}]*\}', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = content
            
            return json.loads(json_str)
            
        except json.JSONDecodeError:
            print(f"Failed to parse JSON from response: {content[:200]}...")
            return {}
    
    def _post_process_fields(self, fields: Dict[str, Any], document_type: DocumentType) -> Dict[str, Any]:
        """Post-process extracted fields for standardization"""
        processed = {}
        
        # Get country information if available (for name parsing)
        country = fields.get('country', None)
        
        for field, value in fields.items():
            if value is None or value == "null":
                processed[field] = None
                continue
            
            # Standardize dates
            if any(date_keyword in field for date_keyword in ["date", "expires"]):
                processed[field] = standardize_date(str(value))
            
            # Handle name fields intelligently
            elif field == "full_name":
                # For passports, we might need to split the full name
                full_name = str(value).strip()
                processed[field] = normalize_name(full_name)
                
                # If the document type expects separate first/last names but we only have full_name
                required_fields = DOCUMENT_FIELDS.get(document_type, {})
                if "first_name" in required_fields or "last_name" in required_fields:
                    # Use intelligent name parsing
                    first_name, last_name = guess_name_order(full_name, country)
                    if "first_name" in required_fields and "first_name" not in fields:
                        processed["first_name"] = normalize_name(first_name)
                    if "last_name" in required_fields and "last_name" not in fields:
                        processed["last_name"] = normalize_name(last_name)
            
            # Handle cases where names are already split but might need normalization
            elif field in ["first_name", "last_name"]:
                processed[field] = normalize_name(str(value))
            
            # Clean up country names
            elif field == "country":
                # Standardize country format
                country_value = str(value).lower().strip()
                # Remove special characters and normalize
                country_value = re.sub(r'[^\w\s]', '', country_value)
                country_value = country_value.replace(' ', '_')
                processed[field] = country_value
            
            else:
                processed[field] = str(value).strip()
        
        # Handle fuzzy name matching - if we have a full name field but need first/last
        if document_type in [DocumentType.DRIVER_LICENSE, DocumentType.EAD_CARD]:
            # These documents typically need separate first/last names
            if "full_name" in fields and ("first_name" not in processed or "last_name" not in processed):
                full_name = fields.get("full_name", "")
                if full_name:
                    first_name, last_name = guess_name_order(full_name, country)
                    if "first_name" not in processed:
                        processed["first_name"] = normalize_name(first_name)
                    if "last_name" not in processed:
                        processed["last_name"] = normalize_name(last_name)
        
        # Ensure all required fields are present
        required_fields = DOCUMENT_FIELDS.get(document_type, {})
        for field in required_fields:
            if field not in processed:
                processed[field] = None
        
        return processed