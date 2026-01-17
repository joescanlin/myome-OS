"""Tests for core module"""

from myome.core.config import get_settings
from myome.core.exceptions import MyomeException


def test_settings_loads():
    """Test that settings can be loaded"""
    settings = get_settings()
    assert settings.app_name == "Myome"
    assert settings.app_version == "0.1.0"


def test_settings_singleton():
    """Test that settings returns cached instance"""
    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1 is settings2


def test_myome_exception():
    """Test custom exception"""
    exc = MyomeException("Test error", {"key": "value"})
    assert exc.message == "Test error"
    assert exc.details == {"key": "value"}
    assert str(exc) == "Test error"
