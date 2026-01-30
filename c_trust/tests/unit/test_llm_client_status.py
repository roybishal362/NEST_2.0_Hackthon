"""
Unit tests for LLM Client get_status() method
"""
import pytest
from unittest.mock import patch, MagicMock
from src.intelligence.llm_client import GroqLLMClient


class TestLLMClientStatus:
    """Test suite for LLM client status functionality"""
    
    def test_get_status_with_valid_api_key(self):
        """Test get_status() returns correct info when API key is valid"""
        with patch('src.intelligence.llm_client.Groq') as mock_groq:
            # Mock successful initialization
            mock_client = MagicMock()
            mock_groq.return_value = mock_client
            
            # Mock successful connection test
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_client.chat.completions.create.return_value = mock_response
            
            # Create client with API key
            client = GroqLLMClient(api_key="test_key_123")
            
            # Get status
            status = client.get_status()
            
            # Verify status structure
            assert isinstance(status, dict)
            assert 'available' in status
            assert 'mock_mode' in status
            assert 'error' in status
            assert 'api_key_configured' in status
            assert 'groq_package_available' in status
            assert 'model' in status
            
            # Verify values for successful initialization
            assert status['available'] is True
            assert status['mock_mode'] is False
            assert status['error'] is None
            assert status['api_key_configured'] is True
            assert status['model'] == "llama-3.1-8b-instant"
    
    def test_get_status_without_api_key(self):
        """Test get_status() when API key is missing"""
        with patch.dict('os.environ', {}, clear=True):
            client = GroqLLMClient()
            
            status = client.get_status()
            
            # Verify mock mode is enabled
            assert status['available'] is False
            assert status['mock_mode'] is True
            assert status['error'] == "GROQ_API_KEY not found in environment"
            assert status['api_key_configured'] is False
    
    def test_get_status_with_connection_failure(self):
        """Test get_status() when connection test fails"""
        with patch('src.intelligence.llm_client.Groq') as mock_groq:
            # Mock failed connection test
            mock_client = MagicMock()
            mock_groq.return_value = mock_client
            mock_client.chat.completions.create.side_effect = Exception("Connection failed")
            
            client = GroqLLMClient(api_key="test_key_123")
            
            status = client.get_status()
            
            # Verify fallback to mock mode
            assert status['available'] is False
            assert status['mock_mode'] is True
            assert "Failed to initialize Groq client" in status['error']
            assert status['api_key_configured'] is True
    
    def test_get_status_with_forced_mock_mode(self):
        """Test get_status() when mock mode is forced"""
        with patch('src.intelligence.llm_client.Groq'):
            client = GroqLLMClient(api_key="test_key_123", mock_mode=True)
            
            status = client.get_status()
            
            # Verify mock mode is enabled even with API key
            assert status['available'] is False
            assert status['mock_mode'] is True
            assert status['api_key_configured'] is True
    
    def test_get_status_includes_model_info(self):
        """Test that get_status() includes model information"""
        with patch('src.intelligence.llm_client.Groq') as mock_groq:
            mock_client = MagicMock()
            mock_groq.return_value = mock_client
            
            # Mock successful connection test
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_client.chat.completions.create.return_value = mock_response
            
            custom_model = "llama-3.1-70b-versatile"
            client = GroqLLMClient(api_key="test_key_123", model=custom_model)
            
            status = client.get_status()
            
            # Verify custom model is included
            assert status['model'] == custom_model
    
    def test_is_available_property(self):
        """Test the is_available property"""
        with patch('src.intelligence.llm_client.Groq') as mock_groq:
            # Test with successful initialization
            mock_client = MagicMock()
            mock_groq.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_client.chat.completions.create.return_value = mock_response
            
            client = GroqLLMClient(api_key="test_key_123")
            assert client.is_available is True
            
        # Test with mock mode
        with patch.dict('os.environ', {}, clear=True):
            client = GroqLLMClient()
            assert client.is_available is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
