"""Vercel Python runtime entrypoint for the public API."""

from backend.app.main import app


__all__ = ["app"]
