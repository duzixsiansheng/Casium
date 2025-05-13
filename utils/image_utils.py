import base64
import io
import tempfile
import os
from typing import List
from PIL import Image
import pdf2image
from fastapi import HTTPException

def process_pdf_to_images(pdf_content: bytes) -> List[Image.Image]:
    """
    Convert PDF to images using pdf2image
    
    Args:
        pdf_content: PDF file content as bytes
        
    Returns:
        List of PIL Image objects
        
    Raises:
        HTTPException: If PDF processing fails
    """
    try:
        import pdf2image
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_content)
            tmp_file.flush()
            
            try:
                images = pdf2image.convert_from_path(tmp_file.name)
                return images
            finally:
                os.unlink(tmp_file.name)
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="PDF support not available. Please install pdf2image and poppler."
        )
    except Exception as e:
        if "poppler" in str(e).lower():
            raise HTTPException(
                status_code=500,
                detail="Poppler is not installed. Please install poppler to process PDF files."
            )
        raise HTTPException(
            status_code=500,
            detail=f"Error processing PDF: {str(e)}"
        )

def image_to_base64(image: Image.Image) -> str:
    """
    Convert PIL Image to base64 string
    
    Args:
        image: PIL Image object
        
    Returns:
        Base64 encoded string
    """
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode()

def validate_file_type(content_type: str, supported_types: List[str]) -> bool:
    """
    Validate if file type is supported
    
    Args:
        content_type: MIME type of the file
        supported_types: List of supported MIME types
        
    Returns:
        True if file type is supported
    """
    return content_type in supported_types

def validate_file_size(content: bytes, max_size: int) -> bool:
    """
    Validate if file size is within limits
    
    Args:
        content: File content as bytes
        max_size: Maximum file size in bytes
        
    Returns:
        True if file size is within limits
    """
    return len(content) <= max_size