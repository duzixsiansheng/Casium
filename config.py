import os
from typing import Optional

class Config:
    """Application configuration"""
    
    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "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")
    
    # OpenAI API settings
    OPENAI_BASE_URL: str = "https://api.openai.com/v1/chat/completions"
    OPENAI_MODEL: str = "gpt-4o"  # Can be gpt-4o, gpt-4-turbo, gpt-4o-mini
    OPENAI_TIMEOUT: int = 30
    
    # API settings
    API_TITLE: str = "Document Processing API"
    API_VERSION: str = "2.0.0"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Processing settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    SUPPORTED_FILE_TYPES: list = ["image/jpeg", "image/png", "image/jpg", "application/pdf"]
    
    # Model settings
    TEMPERATURE: float = 0.1  # Lower temperature for consistent extraction
    MAX_TOKENS: int = 500
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration"""
        if cls.OPENAI_API_KEY == "your-api-key-here":
            print("Warning: OpenAI API key not set. Please set OPENAI_API_KEY environment variable.")
            return False
        return True

# Create global config instance
config = Config()