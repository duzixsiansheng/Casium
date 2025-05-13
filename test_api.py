import httpx
import asyncio
import os
import sys
from typing import Dict, Any

async def test_health(base_url: str) -> bool:
    """Test the health endpoint"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                result = response.json()
                print(f"✓ API Health: {result['status']}")
                print(f"  Version: {result['api_version']}")
                print(f"  Model: {result['model']}")
                return True
            else:
                print(f"✗ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Cannot connect to API: {e}")
            return False

async def test_document_types(base_url: str) -> bool:
    """Test the document types endpoint"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{base_url}/document-types")
            if response.status_code == 200:
                result = response.json()
                print("\n✓ Supported Document Types:")
                for doc_type, fields in result.items():
                    print(f"  {doc_type}: {', '.join(fields)}")
                return True
            else:
                print(f"✗ Document types endpoint failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Error getting document types: {e}")
            return False

async def test_classification(base_url: str, file_path: str) -> Dict[str, Any]:
    """Test document classification"""
    if not os.path.exists(file_path):
        print(f"✗ File not found: {file_path}")
        return None
    
    async with httpx.AsyncClient() as client:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f)}
            
            try:
                response = await client.post(
                    f"{base_url}/classify",
                    files=files,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"\n✓ Classification Result:")
                    print(f"  File: {os.path.basename(file_path)}")
                    print(f"  Document Type: {result['document_type']}")
                    return result
                else:
                    print(f"✗ Classification failed: {response.status_code}")
                    print(f"  Error: {response.text}")
                    return None
                    
            except Exception as e:
                print(f"✗ Error during classification: {e}")
                return None

async def test_extraction(base_url: str, file_path: str) -> Dict[str, Any]:
    """Test field extraction"""
    if not os.path.exists(file_path):
        print(f"✗ File not found: {file_path}")
        return None
    
    async with httpx.AsyncClient() as client:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f)}
            
            try:
                response = await client.post(
                    f"{base_url}/extract",
                    files=files,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"\n✓ Extraction Result:")
                    print(f"  File: {os.path.basename(file_path)}")
                    print(f"  Document Type: {result['document_type']}")
                    print("  Extracted Fields:")
                    
                    for field, value in result['document_content'].items():
                        print(f"    {field}: {value}")
                    
                    return result
                else:
                    print(f"✗ Extraction failed: {response.status_code}")
                    print(f"  Error: {response.text}")
                    return None
                    
            except Exception as e:
                print(f"✗ Error during extraction: {e}")
                return None

async def run_tests(base_url: str, test_files: list):
    """Run all tests"""
    print(f"Testing Document Processing API at {base_url}")
    print("=" * 50)
    
    # Test health
    if not await test_health(base_url):
        print("\nAPI is not healthy. Stopping tests.")
        return
    
    # Test document types
    await test_document_types(base_url)
    
    # Test classification and extraction for each file
    for test_file in test_files:
        print(f"\n{'=' * 30}")
        print(f"Testing file: {test_file}")
        print('=' * 30)
        
        # Test classification (Step 1)
        classification_result = await test_classification(base_url, test_file)
        
        # Test extraction (Step 2)
        extraction_result = await test_extraction(base_url, test_file)
        
        # Compare results
        if classification_result and extraction_result:
            if classification_result['document_type'] == extraction_result['document_type']:
                print("\n✓ Classification and extraction results match")
            else:
                print("\n✗ Classification and extraction results don't match")

async def main():
    """Main test function"""
    base_url = "http://localhost:8000"
    
    # Test files (adjust paths as needed)
    test_files = [
        "test_data/passport_sample.jpg",
        "test_data/driver_license_sample.jpg",
        "test_data/ead_card_sample.jpg",
        "test_data/document.pdf"  # Test PDF if available
    ]
    
    # Filter existing files
    existing_files = [f for f in test_files if os.path.exists(f)]
    
    if not existing_files:
        print("No test files found. Please create a 'test_data' directory with sample documents.")
        print("\nExpected files:")
        for f in test_files:
            print(f"  - {f}")
        return
    
    print(f"Found {len(existing_files)} test files")
    
    # Run tests
    await run_tests(base_url, existing_files)

if __name__ == "__main__":
    asyncio.run(main())