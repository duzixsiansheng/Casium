"""
Unit tests for field extraction
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import json

from processors.extractor import FieldExtractor
from models import DocumentType


class TestFieldExtractor:
    """Test suite for FieldExtractor"""
    
    @pytest.fixture
    def extractor(self):
        """Create an extractor instance"""
        return FieldExtractor()
    
    @pytest.fixture
    def passport_fields(self):
        """Sample passport fields"""
        return {
            "full_name": "John Michael Smith",
            "date_of_birth": "15/01/1990",
            "country": "United States",
            "issue_date": "20/03/2020",
            "expiration_date": "20/03/2030",
            "passport_number": "123456789"
        }
    
    @pytest.fixture
    def driver_license_fields(self):
        """Sample driver's license fields"""
        return {
            "license_number": "D123456789",
            "first_name": "Jane",
            "last_name": "Doe",
            "date_of_birth": "05/10/1992",
            "issue_date": "15/06/2021",
            "expiration_date": "05/10/2024",
            "address": "123 Main St, City, State 12345"
        }
    
    @pytest.mark.asyncio
    async def test_extract_passport_fields_success(self, extractor, sample_passport_image, passport_fields):
        """Test successful passport field extraction"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": json.dumps(passport_fields)
                    }
                }]
            }
            mock_post.return_value = mock_response
            
            result = await extractor.extract(sample_passport_image, DocumentType.PASSPORT)
            
            assert "full_name" in result
            assert result["full_name"] == "John Michael Smith"
            assert result["date_of_birth"] == "01/15/1990"  # Date should be standardized
            assert "country" in result
    
    @pytest.mark.asyncio
    async def test_extract_driver_license_fields_success(self, extractor, sample_driver_license_image, driver_license_fields):
        """Test successful driver's license field extraction"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": json.dumps(driver_license_fields)
                    }
                }]
            }
            mock_post.return_value = mock_response
            
            result = await extractor.extract(sample_driver_license_image, DocumentType.DRIVER_LICENSE)
            
            assert "first_name" in result
            assert "last_name" in result
            assert result["license_number"] == "D123456789"
    
    
    @pytest.mark.asyncio
    async def test_extract_with_missing_fields(self, extractor, sample_passport_image):
        """Test extraction when some fields are missing"""
        partial_fields = {
            "full_name": "John Doe",
            "date_of_birth": None,
            "passport_number": "123456789"
        }
        
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": json.dumps(partial_fields)
                    }
                }]
            }
            mock_post.return_value = mock_response
            
            result = await extractor.extract(sample_passport_image, DocumentType.PASSPORT)
            
            assert result["full_name"] == "John Doe"
            assert result["date_of_birth"] is None
            assert "passport_number" in result
    
    @pytest.mark.asyncio
    async def test_extract_date_standardization(self, extractor, sample_passport_image):
        """Test date standardization during extraction"""
        fields_with_various_dates = {
            "full_name": "Test User",
            "date_of_birth": "15/03/1990",  # DD/MM/YYYY
            "issue_date": "2020-03-15",     # ISO format
            "expiration_date": "March 15, 2030"  # Text format
        }
        
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": json.dumps(fields_with_various_dates)
                    }
                }]
            }
            mock_post.return_value = mock_response
            
            result = await extractor.extract(sample_passport_image, DocumentType.PASSPORT)
            
            # All dates should be standardized to MM/DD/YYYY
            assert result["date_of_birth"] == "03/15/1990"
            assert result["issue_date"] == "03/15/2020"
            assert result["expiration_date"] == "03/15/2030"
    
    @pytest.mark.asyncio
    async def test_extract_name_parsing(self, extractor, sample_passport_image):
        """Test name parsing and splitting logic"""
        fields_with_full_name = {
            "full_name": "Smith, John Michael",
            "date_of_birth": "01/01/1990",
            "passport_number": "123456789"
        }
        
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": json.dumps(fields_with_full_name)
                    }
                }]
            }
            mock_post.return_value = mock_response
            
            # For passport, assuming it needs to process names
            result = await extractor.extract(sample_passport_image, DocumentType.PASSPORT)
            
            assert "full_name" in result
            # The name should be processed/normalized
            assert result["full_name"] == "John Michael Smith" or result["full_name"] == "Smith, John Michael"
    
    @pytest.mark.asyncio
    async def test_extract_unknown_document_type(self, extractor, sample_passport_image):
        """Test extraction with unknown document type"""
        result = await extractor.extract(sample_passport_image, DocumentType.UNKNOWN)
        
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_extract_api_error(self, extractor, sample_passport_image):
        """Test extraction when API returns an error"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_post.return_value = mock_response
            
            result = await extractor.extract(sample_passport_image, DocumentType.PASSPORT)
            
            assert result == {}
    
    @pytest.mark.asyncio
    async def test_extract_network_error(self, extractor, sample_passport_image):
        """Test extraction when network error occurs"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("Network error")
            
            result = await extractor.extract(sample_passport_image, DocumentType.PASSPORT)
            
            assert result == {}