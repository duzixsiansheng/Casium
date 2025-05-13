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
        
        Important Instructions for Name Extraction:
        1. If the document shows a complete name in one field, extract it as "full_name"
        2. If the document shows first and last names in separate fields, extract them as "first_name" and "last_name"
        3. If you can see any name information, extract what you can see
        4. Common patterns to recognize:
           - "SMITH, JOHN" format: extract as full_name (we'll parse it later)
           - Separate fields labeled "First Name" and "Last Name": extract both
           - Single name field: extract as full_name
        
        General Instructions:
        - Extract ONLY what is visible on the document
        - For dates: extract in the format shown (we'll standardize later)
        - For missing fields: use null
        - Do NOT make assumptions or split/combine fields yourself
        
        Example format:
        {example_json}
        
        Return only the JSON object, no additional text.
        """
    
    def _get_field_descriptions(self, document_type: DocumentType) -> Dict[str, str]:
        """Get human-readable descriptions for each field"""
        # Common name field descriptions for all document types
        common_name_fields = {
            "full_name": "Complete name as shown on document",
            "first_name": "First name (given name)",
            "last_name": "Last name (surname/family name)"
        }
        
        descriptions = {
            DocumentType.PASSPORT: {
                **common_name_fields,
                "date_of_birth": "Date of birth (MM/DD/YYYY format)",
                "country": "Issuing country (lowercase with underscores)",
                "issue_date": "Date of issue (MM/DD/YYYY format)",
                "expiration_date": "Expiration date (MM/DD/YYYY format)",
                "passport_number": "Passport number/document number"
            },
            DocumentType.DRIVER_LICENSE: {
                **common_name_fields,
                "license_number": "Driver's license number",
                "date_of_birth": "Date of birth (MM/DD/YYYY format)",
                "issue_date": "Issue date (MM/DD/YYYY format)",
                "expiration_date": "Expiration date (MM/DD/YYYY format)",
                "address": "Full address"
            },
            DocumentType.EAD_CARD: {
                **common_name_fields,
                "card_number": "USCIS card number (with hyphens)",
                "category": "Category code (e.g., C09)",
                "card_expires_date": "Card expiration date (MM/DD/YYYY format)",
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
        
        # Get country information if available (for name parsing and date formatting)
        country = fields.get('country', None)
        
        # Collect all date fields for context-based parsing
        date_fields = []
        for field, value in fields.items():
            if value and any(date_keyword in field for date_keyword in ["date", "expires"]):
                date_fields.append(str(value))
        
        # First, process all extracted fields
        for field, value in fields.items():
            if value is None or value == "null":
                processed[field] = None
                continue
            
            # Standardize dates with country context
            if any(date_keyword in field for date_keyword in ["date", "expires"]):
                # Use the enhanced date standardizer with country and context
                processed[field] = standardize_date(
                    str(value), 
                    country=country,
                    context_dates=date_fields
                )
            
            # Normalize names (but don't split yet)
            elif field in ["full_name", "first_name", "last_name"]:
                processed[field] = normalize_name(str(value))
            
            # Clean up country names
            elif field == "country":
                country_value = str(value).lower().strip()
                country_value = re.sub(r'[^\w\s]', '', country_value)
                country_value = country_value.replace(' ', '_')
                processed[field] = country_value
            
            else:
                processed[field] = str(value).strip()
        
        # Now ensure all three name fields are populated
        # Process in order: full_name first, then first/last names
        
        # Step 1: If we have full_name, ensure we also have first/last
        if "full_name" in processed and processed["full_name"]:
            if "first_name" not in processed or "last_name" not in processed or \
               not processed.get("first_name") or not processed.get("last_name"):
                first_name, last_name = guess_name_order(processed["full_name"], country)
                
                if not processed.get("first_name"):
                    processed["first_name"] = first_name
                
                if not processed.get("last_name"):
                    processed["last_name"] = last_name
        
        # Step 2: If we have first/last but no full_name, create it
        if ("first_name" in processed and processed["first_name"]) or \
           ("last_name" in processed and processed["last_name"]):
            if "full_name" not in processed or not processed.get("full_name"):
                first = processed.get("first_name", "")
                last = processed.get("last_name", "")
                if first or last:
                    processed["full_name"] = f"{first} {last}".strip()
        
        # Step 3: Final validation - ensure all name fields are consistent
        # If we still have any None values in name fields, try to fill them
        if processed.get("full_name") and (not processed.get("first_name") or not processed.get("last_name")):
            first_name, last_name = guess_name_order(processed["full_name"], country)
            if not processed.get("first_name"):
                processed["first_name"] = first_name
            if not processed.get("last_name"):
                processed["last_name"] = last_name
        
        # If we have first and/or last but no full name, create it
        if (processed.get("first_name") or processed.get("last_name")) and not processed.get("full_name"):
            first = processed.get("first_name", "")
            last = processed.get("last_name", "")
            processed["full_name"] = f"{first} {last}".strip()
        
        # Ensure all required fields are present (set to None if missing)
        required_fields = DOCUMENT_FIELDS.get(document_type, {})
        for field in required_fields:
            if field not in processed:
                processed[field] = None
        
        # Final cleanup: if any name field is empty string, convert to None
        for name_field in ["full_name", "first_name", "last_name"]:
            if name_field in processed and processed[name_field] == "":
                processed[name_field] = None
        
        return processed