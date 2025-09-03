import pytest
from unittest.mock import AsyncMock, Mock, patch
from aiohttp import ClientError, ClientResponseError
import aiohttp
from dacwatch.kroki_client import KrokiClient


class TestKrokiClient:
    """Test suite for KrokiClient."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = KrokiClient("https://kroki.io")

    def test_init(self):
        """Test KrokiClient initialization."""
        assert self.client.base_url == "https://kroki.io"

    def test_get_diagram_type_dot(self):
        """Test diagram type detection for .dot files."""
        assert self.client.get_diagram_type("diagram.dot") == "graphviz"

    def test_get_diagram_type_plantuml(self):
        """Test diagram type detection for PlantUML files."""
        assert self.client.get_diagram_type("diagram.puml") == "plantuml"
        assert self.client.get_diagram_type("diagram.plantuml") == "plantuml"

    def test_get_diagram_type_mermaid(self):
        """Test diagram type detection for Mermaid files."""
        assert self.client.get_diagram_type("diagram.mermaid") == "mermaid"

    def test_get_diagram_type_unsupported(self):
        """Test diagram type detection for unsupported files."""
        assert self.client.get_diagram_type("diagram.txt") is None
        assert self.client.get_diagram_type("diagram") is None

    @pytest.mark.asyncio
    async def test_render_diagram_invalid_format(self):
        """Test diagram rendering with invalid format."""
        with pytest.raises(ValueError, match="Format must be 'svg' or 'png'"):
            await self.client.render_diagram("test", "mermaid", "invalid")

    @pytest.mark.asyncio
    async def test_render_diagram_empty_source(self):
        """Test diagram rendering with empty source."""
        with pytest.raises(ValueError, match="Source cannot be empty"):
            await self.client.render_diagram("", "mermaid", "svg")

    @pytest.mark.asyncio
    async def test_render_diagram_none_diagram_type(self):
        """Test diagram rendering with None diagram type."""
        with pytest.raises(ValueError, match="Diagram type cannot be None"):
            await self.client.render_diagram("test", None, "svg")

    @pytest.mark.asyncio
    async def test_render_diagram_integration(self):
        """Integration test with real Kroki service."""
        # Test with a simple diagram that should work
        result = await self.client.render_diagram("digraph G { A -> B }", "graphviz", "svg")
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert b"<svg" in result

    @pytest.mark.asyncio
    async def test_render_diagram_mermaid_integration(self):
        """Integration test with Mermaid diagram."""
        result = await self.client.render_diagram("graph LR\nA --> B", "mermaid", "svg")
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert b"<svg" in result