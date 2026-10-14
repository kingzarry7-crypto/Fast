"""Compatibility ASGI entrypoint for hosts configured with ``main:app``.

The canonical implementation lives in app.py. This module keeps Railway's
common default Uvicorn target working if the service start command is
``uvicorn main:app`` instead of the Dockerfile's ``uvicorn app:app``.
"""
from app import app  # noqa: F401
