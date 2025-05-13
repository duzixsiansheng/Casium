from sqlalchemy import create_engine, Column, String, DateTime, Text, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from datetime import datetime
import uuid

Base = declarative_base()

class Document(Base):
    """Main document table"""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    file_name = Column(String, nullable=False)
    file_path = Column(String)  # Path to stored file
    file_data_url = Column(Text)  # Store the data URL for the image
    document_type = Column(String, nullable=False)  # passport, driver_license, ead_card
    upload_date = Column(DateTime, default=datetime.utcnow)
    last_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String, default="pending")  # pending, extracted, verified, error
    
    # Relationships
    fields = relationship("ExtractedField", back_populates="document", cascade="all, delete-orphan")
    corrections = relationship("FieldCorrection", back_populates="document", cascade="all, delete-orphan")


class ExtractedField(Base):
    """Extracted fields from documents"""
    __tablename__ = "extracted_fields"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    field_name = Column(String, nullable=False)
    original_value = Column(Text)  # Original extracted value
    current_value = Column(Text)   # Current value (may be corrected)
    confidence_score = Column(String)  # Optional confidence score
    extraction_date = Column(DateTime, default=datetime.utcnow)
    is_corrected = Column(Boolean, default=False)
    
    # Relationships
    document = relationship("Document", back_populates="fields")
    corrections = relationship("FieldCorrection", back_populates="field", cascade="all, delete-orphan")


class FieldCorrection(Base):
    """History of manual corrections"""
    __tablename__ = "field_corrections"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    field_id = Column(String, ForeignKey("extracted_fields.id"), nullable=False)
    field_name = Column(String, nullable=False)
    old_value = Column(Text)
    new_value = Column(Text)
    correction_date = Column(DateTime, default=datetime.utcnow)
    corrected_by = Column(String, default="user")  # For multi-user systems
    
    # Relationships
    document = relationship("Document", back_populates="corrections")
    field = relationship("ExtractedField", back_populates="corrections")


class ExtractionHistory(Base):
    """History of extraction attempts"""
    __tablename__ = "extraction_history"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    extraction_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String)  # success, failed
    error_message = Column(Text)
    extracted_data = Column(JSON)  # Store raw extraction result
    
    # Relationships
    document = relationship("Document")


# Create async engine
def get_async_engine(database_url: str = "sqlite+aiosqlite:///./document_processing.db"):
    return create_async_engine(database_url, echo=False)

# Create sync engine for migrations
def get_sync_engine(database_url: str = "sqlite:///./document_processing.db"):
    return create_engine(database_url, echo=False)

# Create tables
def init_db():
    """Initialize database tables"""
    engine = get_sync_engine()
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")

# Async session factory - create only when needed to avoid initialization issues
_async_engine = None
_AsyncSessionLocal = None

def get_async_session():
    """Get async session factory"""
    global _async_engine, _AsyncSessionLocal
    if _async_engine is None:
        _async_engine = get_async_engine()
        _AsyncSessionLocal = sessionmaker(
            bind=_async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    return _AsyncSessionLocal

# Dependency for FastAPI
async def get_db():
    """Get database session"""
    AsyncSessionLocal = get_async_session()
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()