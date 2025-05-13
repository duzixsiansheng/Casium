from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from database.models import Document, ExtractedField, FieldCorrection, ExtractionHistory

class DocumentRepository:
    """Repository for document operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_document(self, file_name: str, document_type: str, file_path: Optional[str] = None, file_data_url: Optional[str] = None) -> Document:
        """Create a new document record"""
        document = Document(
            file_name=file_name,
            file_path=file_path,
            file_data_url=file_data_url,
            document_type=document_type,
            status="pending"
        )
        self.session.add(document)
        await self.session.commit()
        await self.session.refresh(document)
        return document
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        """Get document by ID with all related data"""
        result = await self.session.execute(
            select(Document)
            .options(selectinload(Document.fields))
            .options(selectinload(Document.corrections))
            .where(Document.id == document_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all_documents(self, limit: int = 10, offset: int = 0) -> List[Document]:
        """Get all documents with pagination"""
        result = await self.session.execute(
            select(Document)
            .order_by(Document.upload_date.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    async def update_document_status(self, document_id: str, status: str) -> Optional[Document]:
        """Update document status"""
        await self.session.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(status=status, last_modified=datetime.utcnow())
        )
        await self.session.commit()
        return await self.get_document(document_id)
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete document and all related data"""
        document = await self.get_document(document_id)
        if document:
            await self.session.delete(document)
            await self.session.commit()
            return True
        return False


class FieldRepository:
    """Repository for field operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_extracted_fields(self, document_id: str, fields: Dict[str, Any]) -> List[ExtractedField]:
        """Create extracted fields for a document"""
        extracted_fields = []
        
        for field_name, value in fields.items():
            field = ExtractedField(
                document_id=document_id,
                field_name=field_name,
                original_value=str(value) if value is not None else None,
                current_value=str(value) if value is not None else None
            )
            self.session.add(field)
            extracted_fields.append(field)
        
        await self.session.commit()
        return extracted_fields
    
    async def update_field_value(self, field_id: str, new_value: str, user: str = "user") -> Optional[ExtractedField]:
        """Update field value and create correction record"""
        # Get current field
        result = await self.session.execute(
            select(ExtractedField).where(ExtractedField.id == field_id)
        )
        field = result.scalar_one_or_none()
        
        if not field:
            return None
        
        # Create correction record
        correction = FieldCorrection(
            document_id=field.document_id,
            field_id=field_id,
            field_name=field.field_name,
            old_value=field.current_value,
            new_value=new_value,
            corrected_by=user
        )
        self.session.add(correction)
        
        # Update field
        field.current_value = new_value
        field.is_corrected = True
        
        await self.session.commit()
        await self.session.refresh(field)
        return field
    
    async def get_document_fields(self, document_id: str) -> List[ExtractedField]:
        """Get all fields for a document"""
        result = await self.session.execute(
            select(ExtractedField)
            .where(ExtractedField.document_id == document_id)
            .order_by(ExtractedField.field_name)
        )
        return result.scalars().all()
    
    async def get_field_corrections(self, field_id: str) -> List[FieldCorrection]:
        """Get correction history for a field"""
        result = await self.session.execute(
            select(FieldCorrection)
            .where(FieldCorrection.field_id == field_id)
            .order_by(FieldCorrection.correction_date.desc())
        )
        return result.scalars().all()


class ExtractionHistoryRepository:
    """Repository for extraction history operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_extraction_record(
        self, 
        document_id: str, 
        status: str, 
        extracted_data: Optional[Dict] = None,
        error_message: Optional[str] = None
    ) -> ExtractionHistory:
        """Create extraction history record"""
        record = ExtractionHistory(
            document_id=document_id,
            status=status,
            extracted_data=extracted_data,
            error_message=error_message
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record
    
    async def get_document_history(self, document_id: str) -> List[ExtractionHistory]:
        """Get extraction history for a document"""
        result = await self.session.execute(
            select(ExtractionHistory)
            .where(ExtractionHistory.document_id == document_id)
            .order_by(ExtractionHistory.extraction_date.desc())
        )
        return result.scalars().all()


class DatabaseService:
    """Main database service combining all repositories"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.documents = DocumentRepository(session)
        self.fields = FieldRepository(session)
        self.history = ExtractionHistoryRepository(session)
    
    async def process_extraction_result(
        self, 
        file_name: str,
        document_type: str,
        extracted_fields: Dict[str, Any],
        file_path: Optional[str] = None,
        file_data_url: Optional[str] = None
    ) -> Document:
        """Process extraction result and save to database"""
        # Create document
        document = await self.documents.create_document(
            file_name=file_name,
            document_type=document_type,
            file_path=file_path,
            file_data_url=file_data_url
        )
        
        try:
            # Create extracted fields
            await self.fields.create_extracted_fields(document.id, extracted_fields)
            
            # Update document status
            await self.documents.update_document_status(document.id, "extracted")
            
            # Create history record
            await self.history.create_extraction_record(
                document_id=document.id,
                status="success",
                extracted_data=extracted_fields
            )
            
            # Get complete document with fields
            return await self.documents.get_document(document.id)
            
        except Exception as e:
            # On error, update status and create error record
            await self.documents.update_document_status(document.id, "error")
            await self.history.create_extraction_record(
                document_id=document.id,
                status="failed",
                error_message=str(e)
            )
            raise
    
    async def update_field(self, field_id: str, new_value: str, user: str = "user") -> Optional[ExtractedField]:
        """Update field value with correction tracking"""
        field = await self.fields.update_field_value(field_id, new_value, user)
        
        if field:
            # Update document last_modified
            await self.documents.update_document_status(field.document_id, "verified")
        
        return field
    
    async def get_recent_documents(self, limit: int = 10) -> List[Document]:
        """Get recent documents"""
        return await self.documents.get_all_documents(limit=limit)
    
    async def get_document_with_fields(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document with all fields formatted for API response"""
        document = await self.documents.get_document(document_id)
        if not document:
            return None
        
        fields = await self.fields.get_document_fields(document_id)
        
        # Format response
        return {
            "id": document.id,
            "file_name": document.file_name,
            "file_data_url": document.file_data_url,
            "document_type": document.document_type,
            "upload_date": document.upload_date.isoformat(),
            "last_modified": document.last_modified.isoformat(),
            "status": document.status,
            "fields": {
                field.field_name: {
                    "id": field.id,
                    "original_value": field.original_value,
                    "current_value": field.current_value,
                    "is_corrected": field.is_corrected
                }
                for field in fields
            }
        }