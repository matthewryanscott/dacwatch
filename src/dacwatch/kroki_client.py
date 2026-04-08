import aiohttp
from typing import Optional
from pathlib import Path


class KrokiError(Exception):
    """Error from the Kroki rendering service."""
    def __init__(self, status: int, reason: str, body: str, url: str = ""):
        self.status = status
        self.reason = reason
        self.body = body
        self.url = url
        super().__init__(f"{status}, message='{reason}', url='{url}'")


class KrokiClient:
    """Client for interacting with Kroki diagram rendering service."""

    def __init__(self, base_url: str, request_timeout: float = 10.0):
        """Initialize the Kroki client.

        Args:
            base_url: Base URL of the Kroki service (e.g., "https://kroki.io")
            request_timeout: Total timeout in seconds for individual requests
        """
        self.base_url = base_url.rstrip("/")
        self.request_timeout = request_timeout

    def get_diagram_type(self, filepath: str) -> Optional[str]:
        """Get the diagram type based on file extension.

        Args:
            filepath: Path to the diagram file

        Returns:
            Diagram type string or None if unsupported
        """
        path = Path(filepath)
        extension = path.suffix.lower()

        type_map = {
            ".dot": "graphviz",
            ".puml": "plantuml",
            ".plantuml": "plantuml",
            ".mermaid": "mermaid"
        }

        return type_map.get(extension)

    async def render_diagram(self, source: str, diagram_type: str, format: str = "svg") -> bytes:
        """Render a diagram using the Kroki service.

        Args:
            source: Diagram source code
            diagram_type: Type of diagram (graphviz, plantuml, mermaid, etc.)
            format: Output format ("svg" or "png")

        Returns:
            Rendered diagram as bytes

        Raises:
            ValueError: If parameters are invalid
            aiohttp.ClientError: If HTTP request fails
        """
        if not source:
            raise ValueError("Source cannot be empty")

        if not diagram_type:
            raise ValueError("Diagram type cannot be None")

        if format not in ["svg", "png"]:
            raise ValueError("Format must be 'svg' or 'png'")

        url = f"{self.base_url}/{diagram_type}/{format}"
        timeout = aiohttp.ClientTimeout(total=self.request_timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, data=source.encode('utf-8')) as response:
                if response.status >= 400:
                    # Get raw error response body for textarea display
                    error_body = await response.text()

                    raise KrokiError(response.status, response.reason, error_body, url=url)

                return await response.read()

    async def check_connection(self):
        """Validate that the configured Kroki service is healthy."""
        url = f"{self.base_url}/health"
        timeout = aiohttp.ClientTimeout(total=self.request_timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status >= 400:
                    error_body = await response.text()
                    raise KrokiError(response.status, response.reason, error_body, url=url)

                await response.read()