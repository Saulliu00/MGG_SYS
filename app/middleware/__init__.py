"""Middleware package for MGG_SYS"""
from .timeout import init_timeout_middleware, with_timeout, TimeoutError

__all__ = [
    'init_timeout_middleware',
    'with_timeout',
    'TimeoutError'
]
