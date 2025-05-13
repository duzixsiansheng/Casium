#!/usr/bin/env python3
"""
Initialize the database for the Document Processing application
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from database.models import init_db, Base, get_sync_engine
from sqlalchemy.orm import sessionmaker
from database.models import Document, ExtractedField, FieldCorrection, ExtractionHistory

def create_sample_data():
    """Create some sample data for testing"""
    engine = get_sync_engine()
    SessionLocal = sessionmaker(bind=engine)
    
    with SessionLocal() as session:
        # Create a sample document
        sample_doc = Document(
            file_name="sample_passport.jpg",
            document_type="passport",
            status="extracted"
        )
        session.add(sample_doc)
        session.commit()
        
        # Create sample fields
        fields = [
            ExtractedField(
                document_id=sample_doc.id,
                field_name="full_name",
                original_value="JOHN DOE",
                current_value="JOHN DOE"
            ),
            ExtractedField(
                document_id=sample_doc.id,
                field_name="date_of_birth",
                original_value="01/15/1990",
                current_value="01/15/1990"
            ),
            ExtractedField(
                document_id=sample_doc.id,
                field_name="passport_number",
                original_value="123456789",
                current_value="123456789"
            )
        ]
        
        for field in fields:
            session.add(field)
        
        session.commit()
        print(f"Created sample document with ID: {sample_doc.id}")

def main():
    """Initialize database"""
    print("Initializing database...")
    
    # Create tables
    init_db()
    
    # Ask if user wants sample data
    response = input("Do you want to create sample data? (y/n): ")
    if response.lower() == 'y':
        create_sample_data()
        print("Sample data created successfully!")
    
    print("Database initialization complete!")

if __name__ == "__main__":
    main()