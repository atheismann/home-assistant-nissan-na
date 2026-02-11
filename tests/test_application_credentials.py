"""Tests for application_credentials.py to reach 90%+ coverage"""
import pytest
from unittest.mock import Mock

from homeassistant.components.application_credentials import AuthorizationServer


class TestAuthorizationServer:
    """Tests for AUTHORIZATION_SERVER constant"""
    
    def test_authorization_server_exists(self):
        """Test AUTHORIZATION_SERVER constant exists"""
        from custom_components.nissan_na.application_credentials import AUTHORIZATION_SERVER
        
        assert AUTHORIZATION_SERVER is not None
        assert isinstance(AUTHORIZATION_SERVER, AuthorizationServer)
    
    def test_authorization_server_authorize_url(self):
        """Test AUTHORIZATION_SERVER has correct authorize URL"""
        from custom_components.nissan_na.application_credentials import AUTHORIZATION_SERVER
        
        assert AUTHORIZATION_SERVER.authorize_url == "https://connect.smartcar.com/oauth/authorize"
    
    def test_authorization_server_token_url(self):
        """Test AUTHORIZATION_SERVER has correct token URL"""
        from custom_components.nissan_na.application_credentials import AUTHORIZATION_SERVER
        
        assert AUTHORIZATION_SERVER.token_url == "https://connect.smartcar.com/oauth/token"


class TestAsyncGetAuthorizationServer:
    """Tests for async_get_authorization_server function"""
    
    @pytest.mark.asyncio
    async def test_async_get_authorization_server_returns_server(self):
        """Test async_get_authorization_server returns AuthorizationServer"""
        from custom_components.nissan_na.application_credentials import async_get_authorization_server, AUTHORIZATION_SERVER
        
        mock_hass = Mock()
        
        result = await async_get_authorization_server(mock_hass)
        
        assert result is AUTHORIZATION_SERVER
        assert isinstance(result, AuthorizationServer)
    
    @pytest.mark.asyncio
    async def test_async_get_authorization_server_with_different_hass(self):
        """Test async_get_authorization_server works with different hass instances"""
        from custom_components.nissan_na.application_credentials import async_get_authorization_server, AUTHORIZATION_SERVER
        
        mock_hass1 = Mock()
        mock_hass2 = Mock()
        
        result1 = await async_get_authorization_server(mock_hass1)
        result2 = await async_get_authorization_server(mock_hass2)
        
        # Should return same singleton instance
        assert result1 is AUTHORIZATION_SERVER
        assert result2 is AUTHORIZATION_SERVER
        assert result1 is result2


class TestAsyncGetDescriptionPlaceholders:
    """Tests for async_get_description_placeholders function"""
    
    @pytest.mark.asyncio
    async def test_async_get_description_placeholders_returns_dict(self):
        """Test async_get_description_placeholders returns a dictionary"""
        from custom_components.nissan_na.application_credentials import async_get_description_placeholders
        
        mock_hass = Mock()
        
        result = await async_get_description_placeholders(mock_hass)
        
        assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_async_get_description_placeholders_has_setup_url(self):
        """Test async_get_description_placeholders includes setup_url"""
        from custom_components.nissan_na.application_credentials import async_get_description_placeholders
        
        mock_hass = Mock()
        
        result = await async_get_description_placeholders(mock_hass)
        
        assert "setup_url" in result
        assert result["setup_url"] == "https://dashboard.smartcar.com"
    
    @pytest.mark.asyncio
    async def test_async_get_description_placeholders_has_more_info_url(self):
        """Test async_get_description_placeholders includes more_info_url"""
        from custom_components.nissan_na.application_credentials import async_get_description_placeholders
        
        mock_hass = Mock()
        
        result = await async_get_description_placeholders(mock_hass)
        
        assert "more_info_url" in result
        assert result["more_info_url"] == "https://github.com/atheismann/home-assistant-nissan-na"
    
    @pytest.mark.asyncio
    async def test_async_get_description_placeholders_urls_are_https(self):
        """Test async_get_description_placeholders URLs use HTTPS"""
        from custom_components.nissan_na.application_credentials import async_get_description_placeholders
        
        mock_hass = Mock()
        
        result = await async_get_description_placeholders(mock_hass)
        
        assert result["setup_url"].startswith("https://")
        assert result["more_info_url"].startswith("https://")
    
    @pytest.mark.asyncio
    async def test_async_get_description_placeholders_with_different_hass(self):
        """Test async_get_description_placeholders works with different hass instances"""
        from custom_components.nissan_na.application_credentials import async_get_description_placeholders
        
        mock_hass1 = Mock()
        mock_hass2 = Mock()
        
        result1 = await async_get_description_placeholders(mock_hass1)
        result2 = await async_get_description_placeholders(mock_hass2)
        
        # Should return consistent data
        assert result1 == result2
        assert result1["setup_url"] == result2["setup_url"]
        assert result1["more_info_url"] == result2["more_info_url"]
