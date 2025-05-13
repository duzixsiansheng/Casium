from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import base64
import io
from PIL import Image
from typing import Dict, Any
import os
import shutil
from pathlib import Path

from models import ClassificationResponse, FieldExtractionResponse, DocumentType, DOCUMENT_FIELDS
from processors import DocumentClassifier, FieldExtractor
from utils import process_pdf_to_images, image_to_base64
from config import config
from database.models import init_db, get_db
from database.operations import DatabaseService
from sqlalchemy.ext.asyncio import AsyncSession

# Initialize processors
classifier = DocumentClassifier()
extractor = FieldExtractor()

# Create upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    init_db()  # Initialize database tables
    
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

# Step 2: Field extraction endpoint with database persistence
@app.post("/extract", response_model=FieldExtractionResponse)
async def extract_fields(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Classify document and extract fields (Step 2) with database persistence
    
    Args:
        file: Uploaded file (image or PDF)
        db: Database session
        
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
    
    # Save uploaded file
    file_path = UPLOAD_DIR / f"{os.urandom(16).hex()}_{file.filename}"
    with open(file_path, "wb") as f:
        f.write(content)
    
    try:
        # Process PDF or image
        image_base64 = None
        file_data_url = None
        
        if file.content_type == "application/pdf":
            images = process_pdf_to_images(content)
            if not images:
                raise HTTPException(status_code=400, detail="Could not extract images from PDF")
            image = images[0]  # Use first page
            image_base64 = image_to_base64(image)
            # Create data URL for PDF preview
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            file_data_url = f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"
        else:
            image = Image.open(io.BytesIO(content))
            image_base64 = base64.b64encode(content).decode()
            # Create data URL for image
            file_data_url = f"data:{file.content_type};base64,{image_base64}"
        
        # Classify document
        document_type = await classifier.classify(image_base64)
        
        # Extract fields
        fields = {}
        if document_type != DocumentType.UNKNOWN:
            fields = await extractor.extract(image_base64, document_type)
        
        # Save to database with data URL
        db_service = DatabaseService(db)
        document = await db_service.process_extraction_result(
            file_name=file.filename,
            document_type=document_type.value,
            extracted_fields=fields,
            file_path=str(file_path),
            file_data_url=file_data_url
        )
        
        return FieldExtractionResponse(
            document_type=document_type,
            document_content=fields
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Clean up file on error
        if file_path.exists():
            file_path.unlink()
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

# New database endpoints
@app.get("/documents")
async def get_documents(
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get recent documents with pagination"""
    db_service = DatabaseService(db)
    documents = await db_service.documents.get_all_documents(limit, offset)
    
    # Format response
    return {
        "documents": [
            {
                "id": doc.id,
                "file_name": doc.file_name,
                "document_type": doc.document_type,
                "upload_date": doc.upload_date.isoformat(),
                "status": doc.status,
                "file_data_url": doc.file_data_url  # Include the data URL
            }
            for doc in documents
        ],
        "total": len(documents)
    }

@app.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get document with all fields"""
    db_service = DatabaseService(db)
    document = await db_service.get_document_with_fields(document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return document

@app.put("/fields/{field_id}")
async def update_field(
    field_id: str,
    update_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Update field value and track correction"""
    new_value = update_data.get("value")
    if new_value is None:
        raise HTTPException(status_code=400, detail="New value is required")
    
    db_service = DatabaseService(db)
    field = await db_service.update_field(field_id, str(new_value))
    
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    
    return {
        "id": field.id,
        "field_name": field.field_name,
        "original_value": field.original_value,
        "current_value": field.current_value,
        "is_corrected": field.is_corrected
    }

@app.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete document and all related data"""
    db_service = DatabaseService(db)
    
    # Get document before deletion to find file path
    document = await db_service.documents.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete from database
    deleted = await db_service.documents.delete_document(document_id)
    
    # Delete the file if it exists
    if document.file_path:
        file_path = Path(document.file_path)
        if file_path.exists():
            file_path.unlink()
    
    return {"message": "Document deleted successfully"}

@app.get("/documents/{document_id}/history")
async def get_document_history(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get extraction history for a document"""
    db_service = DatabaseService(db)
    history = await db_service.history.get_document_history(document_id)
    
    return {
        "history": [
            {
                "id": record.id,
                "extraction_date": record.extraction_date.isoformat(),
                "status": record.status,
                "error_message": record.error_message,
                "extracted_data": record.extracted_data
            }
            for record in history
        ]
    }

@app.get("/documents/{document_id}/corrections")
async def get_document_corrections(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all corrections for a document"""
    db_service = DatabaseService(db)
    document = await db_service.documents.get_document(document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    corrections = []
    for field in document.fields:
        field_corrections = await db_service.fields.get_field_corrections(field.id)
        corrections.extend([
            {
                "field_name": correction.field_name,
                "old_value": correction.old_value,
                "new_value": correction.new_value,
                "correction_date": correction.correction_date.isoformat(),
                "corrected_by": correction.corrected_by
            }
            for correction in field_corrections
        ])
    
    return {"corrections": corrections}

@app.get("/documents/{document_id}/image")
async def get_document_image(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get the image file for a document"""
    db_service = DatabaseService(db)
    document = await db_service.documents.get_document(document_id)
    
    if not document or not document.file_path:
        raise HTTPException(status_code=404, detail="Document or image not found")
    
    file_path = Path(document.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found")
    
    # Determine content type based on file extension
    content_type = "image/jpeg"  # Default
    if file_path.suffix.lower() == ".png":
        content_type = "image/png"
    elif file_path.suffix.lower() == ".pdf":
        content_type = "application/pdf"
    
    # Read and return the file
    with open(file_path, "rb") as f:
        content = f.read()
    
    return Response(content=content, media_type=content_type)

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