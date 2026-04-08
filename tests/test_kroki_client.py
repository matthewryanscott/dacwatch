import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp
from dacwatch.kroki_client import KrokiClient, KrokiError


class TestKrokiClient:
    """Test suite for KrokiClient."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = KrokiClient("https://kroki.io")

    def test_init(self):
        """Test KrokiClient initialization."""
        assert self.client.base_url == "https://kroki.io"
        assert self.client.request_timeout == 10.0

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

    @pytest.mark.asyncio
    async def test_check_connection_uses_health_endpoint(self):
        """Health check should validate Kroki with the /health endpoint."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"ok")

        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response

        with patch("dacwatch.kroki_client.aiohttp.ClientSession") as mock_client_session:
            mock_client_session.return_value.__aenter__.return_value = mock_session

            await self.client.check_connection()

        mock_session.get.assert_called_once_with("https://kroki.io/health")
        mock_response.read.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_check_connection_raises_kroki_error_for_unhealthy_response(self):
        """Health check should surface HTTP failures from the /health endpoint."""
        mock_response = AsyncMock()
        mock_response.status = 503
        mock_response.reason = "Service Unavailable"
        mock_response.text = AsyncMock(return_value="starting up")

        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response

        with patch("dacwatch.kroki_client.aiohttp.ClientSession") as mock_client_session:
            mock_client_session.return_value.__aenter__.return_value = mock_session

            with pytest.raises(KrokiError) as exc_info:
                await self.client.check_connection()

        assert exc_info.value.status == 503
        assert exc_info.value.reason == "Service Unavailable"
        assert exc_info.value.body == "starting up"


def test_kroki_error_is_importable():
    """KrokiError should be importable from kroki_client module."""
    from dacwatch.kroki_client import KrokiError
    assert issubclass(KrokiError, Exception)

def test_kroki_error_has_attributes():
    from dacwatch.kroki_client import KrokiError
    err = KrokiError(400, "Bad Request", "syntax error in diagram")
    assert err.status == 400
    assert err.reason == "Bad Request"
    assert err.body == "syntax error in diagram"
    assert "400" in str(err)