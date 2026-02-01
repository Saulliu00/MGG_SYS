"""Custom exception classes for MGG_SYS"""


class AppError(Exception):
    """Base exception class for all application errors"""
    def __init__(self, message, code=500):
        self.message = message
        self.code = code
        super().__init__(self.message)


class FileValidationError(AppError):
    """Exception raised when file validation fails"""
    def __init__(self, message):
        super().__init__(message, code=400)


class SimulationError(AppError):
    """Exception raised when simulation execution fails"""
    def __init__(self, message):
        super().__init__(message, code=500)


class SubprocessError(AppError):
    """Exception raised when subprocess execution fails"""
    def __init__(self, message, stderr=None):
        self.stderr = stderr
        super().__init__(message, code=500)


class SubprocessTimeoutError(SubprocessError):
    """Exception raised when subprocess execution times out"""
    def __init__(self, message):
        super().__init__(message, code=408)


class DataProcessingError(AppError):
    """Exception raised when data processing fails"""
    def __init__(self, message):
        super().__init__(message, code=500)


class ValidationError(AppError):
    """Exception raised when input validation fails"""
    def __init__(self, message, errors=None):
        self.errors = errors or []
        super().__init__(message, code=400)
