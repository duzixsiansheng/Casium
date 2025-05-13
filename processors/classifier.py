import httpx
from typing import Optional
from models import DocumentType
from config import config

class DocumentClassifier:
    """Document classification using vision LLM"""
    
    def __init__(self):
        self.api_key = config.OPENAI_API_KEY
        self.base_url = config.OPENAI_BASE_URL
        self.model = config.OPENAI_MODEL
        self.timeout = config.OPENAI_TIMEOUT
    
    async def classify(self, image_base64: str) -> DocumentType:
        """
        Classify document type from image
        
        Args:
            image_base64: Base64 encoded image
            
        Returns:
            DocumentType enum value
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = """
        Please analyze this image and determine what type of immigration document it is.
        Classify it as one of the following:
        - passport: International travel document
        - driver_license: State-issued driver's license
        - ead_card: Employment Authorization Document (EAD) card
        
        Only respond with one of these exact words: passport, driver_license, ead_card, or unknown
        """
        
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
            "max_tokens": 50,
            "temperature": 0
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
                    print(f"Classification error: {response.status_code} - {response.text}")
                    return DocumentType.UNKNOWN
                
                result = response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    classification = result["choices"][0]["message"]["content"].strip().lower()
                    
                    if classification in [doc_type.value for doc_type in DocumentType]:
                        return DocumentType(classification)
                
                return DocumentType.UNKNOWN
                    
            except Exception as e:
                print(f"Error during classification: {str(e)}")
                return DocumentType.UNKNOWN