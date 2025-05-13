#!/usr/bin/env python3
"""
Reset and reinitialize the database
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

def reset_database():
    """Delete and recreate the database"""
    db_path = Path("document_processing.db")
    
    # Delete existing database
    if db_path.exists():
        print(f"Deleting existing database: {db_path}")
        db_path.unlink()
    
    # Also delete any journal files
    journal_path = Path("document_processing.db-journal")
    if journal_path.exists():
        journal_path.unlink()
    
    # Import and initialize after deletion
    from database.models import init_db
    
    print("Creating new database...")
    init_db()
    print("Database reset complete!")

if __name__ == "__main__":
    response = input("This will delete all data in the database. Continue? (y/N): ")
    if response.lower() == 'y':
        reset_database()
    else:
        print("Cancelled.")