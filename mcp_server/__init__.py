"""MCP сервер для поиска научных статей"""

from .server import mcp, search_scientific_papers, health_check

__all__ = ["mcp", "search_scientific_papers", "health_check"]