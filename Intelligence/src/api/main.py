"""
FIN AI Microservice Entry Point Module.
Provides top-level app and factory imports.
"""

from .app import app, create_app

__all__ = ["app", "create_app"]
