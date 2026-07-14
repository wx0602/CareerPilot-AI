"""CareerPilot AI knowledge layer.

The public functions exposed here are intentionally framework independent so
the backend and the agent layer can import them without starting FastAPI.
"""

from .rag.service import KnowledgeService

__all__ = ["KnowledgeService"]
