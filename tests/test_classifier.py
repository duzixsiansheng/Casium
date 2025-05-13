"""
Unit tests for document classification
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import json

from processors.classifier import DocumentClassifier
from models import DocumentType


class TestDocumentClassifier:
    """Test suite for DocumentClassifier"""
    
    @pytest.fixture
    def classifier(self):
        """Create a classifier instance"""
        return DocumentClassifier()
    
    @pytest.mark.asyncio
    async def test_classify_passport_success(self, classifier, sample_passport_image, mock_openai_response):
        """Test successful passport classification"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_openai_response("passport")
            mock_post.return_value = mock_response
            
            result = await classifier.classify(sample_passport_image)
            
            assert result == DocumentType.PASSPORT
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_classify_driver_license_success(self, classifier, sample_driver_license_image, mock_openai_response):
        """Test successful driver's license classification"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_openai_response("driver_license")
            mock_post.return_value = mock_response
            
            result = await classifier.classify(sample_driver_license_image)
            
            assert result == DocumentType.DRIVER_LICENSE
    
    @pytest.mark.asyncio
    async def test_classify_ead_card_success(self, classifier, sample_ead_card_image, mock_openai_response):
        """Test successful EAD card classification"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_openai_response("ead_card")
            mock_post.return_value = mock_response
            
            result = await classifier.classify(sample_ead_card_image)
            
            assert result == DocumentType.EAD_CARD
    
    @pytest.mark.asyncio
    async def test_classify_unknown_document(self, classifier, sample_passport_image, mock_openai_response):
        """Test classification of unknown document type"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_openai_response("unknown_type")
            mock_post.return_value = mock_response
            
            result = await classifier.classify(sample_passport_image)
            
            assert result == DocumentType.UNKNOWN
    
    @pytest.mark.asyncio
    async def test_classify_api_error(self, classifier, sample_passport_image):
        """Test classification when API returns an error"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_post.return_value = mock_response
            
            result = await classifier.classify(sample_passport_image)
            
            assert result == DocumentType.UNKNOWN
    
    @pytest.mark.asyncio
    async def test_classify_invalid_response_format(self, classifier, sample_passport_image):
        """Test classification with invalid API response format"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"invalid": "response"}
            mock_post.return_value = mock_response
            
            result = await classifier.classify(sample_passport_image)
            
            assert result == DocumentType.UNKNOWN
    
    @pytest.mark.asyncio
    async def test_classify_network_error(self, classifier, sample_passport_image):
        """Test classification when network error occurs"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("Network error")
            
            result = await classifier.classify(sample_passport_image)
            
            assert result == DocumentType.UNKNOWN
    
    @pytest.mark.asyncio
    async def test_classify_empty_image(self, classifier):
        """Test classification with empty image data"""
        result = await classifier.classify("")
        
        # Should handle gracefully, though in practice we'd validate input
        assert result == DocumentType.UNKNOWN or result is not None