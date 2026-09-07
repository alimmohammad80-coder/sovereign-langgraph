"""
Compatibility entrypoint for Sovereign Intelligence AI.

The canonical FastAPI application lives in app.main.
Keeping this wrapper ensures older commands such as `uvicorn main:app`
continue to work without maintaining a second, divergent application.
"""

from app.main import app

__all__ = ["app"]
