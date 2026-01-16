"""Custom exceptions for Myome"""

from typing import Any


class MyomeException(Exception):
    """Base exception for all Myome errors"""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class DatabaseException(MyomeException):
    """Database operation errors"""
    pass


class SensorException(MyomeException):
    """Sensor connection or data errors"""
    pass


class ValidationException(MyomeException):
    """Data validation errors"""
    pass


class AuthenticationException(MyomeException):
    """Authentication and authorization errors"""
    pass


class EncryptionException(MyomeException):
    """Encryption/decryption errors"""
    pass


class AnalyticsException(MyomeException):
    """Analytics computation errors"""
    pass
