from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import base64
import io
from PIL import Image
from typing import Dict, Any

from models import ClassificationResponse, FieldExtractionResponse, DocumentType, DOCUMENT_FIELDS
from processors import DocumentClassifier, FieldExtractor
from utils import process_pdf_to_images, image_to_base64
from config import config

# Initialize processors
classifier = DocumentClassifier()
extractor = FieldExtractor()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    if not config.validate():
        print("Warning: Configuration validation failed")
    else:
        print("Configuration validated successfully")
    print(f"Starting {config.API_TITLE} v{config.API_VERSION}")
    print(f"Using OpenAI model: {config.OPENAI_MODEL}")
    
    yield
    
    # Shutdown
    print("Shutting down application...")

# Create FastAPI app with lifespan
app = FastAPI(
    title=config.API_TITLE,
    version=config.API_VERSION,
    lifespan=lifespan
)


# Step 1: Classification endpoint
@app.post("/classify", response_model=ClassificationResponse)
async def classify_document(file: UploadFile = File(...)):
    """
    Classify an uploaded document (Step 1 compatibility)
    
    Args:
        file: Uploaded file (image or PDF)
        
    Returns:
        Document classification result
    """
    # Validate file type
    if file.content_type not in config.SUPPORTED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Supported types: {config.SUPPORTED_FILE_TYPES}"
        )
    
    # Read file content
    content = await file.read()
    
    # Validate file size
    if len(content) > config.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {config.MAX_FILE_SIZE} bytes"
        )
    
    try:
        # Process PDF or image
        if file.content_type == "application/pdf":
            images = process_pdf_to_images(content)
            if not images:
                raise HTTPException(status_code=400, detail="Could not extract images from PDF")
            image = images[0]  # Use first page
            image_base64 = image_to_base64(image)
        else:
            image = Image.open(io.BytesIO(content))
            image_base64 = base64.b64encode(content).decode()
        
        # Classify document
        document_type = await classifier.classify(image_base64)
        
        return ClassificationResponse(document_type=document_type)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing document: {str(e)}"
        )

# Step 2: Field extraction endpoint
@app.post("/extract", response_model=FieldExtractionResponse)
async def extract_fields(file: UploadFile = File(...)):
    """
    Classify document and extract fields (Step 2)
    
    Args:
        file: Uploaded file (image or PDF)
        
    Returns:
        Document type and extracted fields
    """
    # Validate file type
    if file.content_type not in config.SUPPORTED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Supported types: {config.SUPPORTED_FILE_TYPES}"
        )
    
    # Read file content
    content = await file.read()
    
    # Validate file size
    if len(content) > config.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {config.MAX_FILE_SIZE} bytes"
        )
    
    try:
        # Process PDF or image
        if file.content_type == "application/pdf":
            images = process_pdf_to_images(content)
            if not images:
                raise HTTPException(status_code=400, detail="Could not extract images from PDF")
            image = images[0]  # Use first page
            image_base64 = image_to_base64(image)
        else:
            image = Image.open(io.BytesIO(content))
            image_base64 = base64.b64encode(content).decode()
        
        # Classify document
        document_type = await classifier.classify(image_base64)
        
        # Extract fields
        fields = {}
        if document_type != DocumentType.UNKNOWN:
            fields = await extractor.extract(image_base64, document_type)
        
        return FieldExtractionResponse(
            document_type=document_type,
            document_content=fields
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing document: {str(e)}"
        )

# Utility endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": config.API_TITLE,
        "version": config.API_VERSION,
        "endpoints": {
            "classify": "/classify",
            "extract": "/extract",
            "health": "/health",
            "document-types": "/document-types"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "api_version": config.API_VERSION,
        "model": config.OPENAI_MODEL
    }

@app.get("/document-types")
async def get_document_types():
    """
    Get supported document types and their fields
    
    Returns:
        Dictionary of document types and their fields
    """
    return {
        doc_type.value: list(fields.keys()) 
        for doc_type, fields in DOCUMENT_FIELDS.items()
    }

if __name__ == "__main__":
    import uvicorn
    
    # Validate configuration
    if not config.validate():
        print("Error: Invalid configuration. Please check your settings.")
        exit(1)
    
    # Run the application
    uvicorn.run(
        "main:app",  # Use import string for reload to work
        host=config.API_HOST, 
        port=config.API_PORT,
        reload=True
    )