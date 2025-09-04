import aiohttp
from typing import Optional
from pathlib import Path


class KrokiClient:
    """Client for interacting with Kroki diagram rendering service."""

    def __init__(self, base_url: str):
        """Initialize the Kroki client.

        Args:
            base_url: Base URL of the Kroki service (e.g., "https://kroki.io")
        """
        self.base_url = base_url.rstrip("/")

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

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=source.encode('utf-8')) as response:
                if response.status >= 400:
                    # Get raw error response body for textarea display
                    error_body = await response.text()
                    
                    # Create a custom exception that includes the raw response body
                    class KrokiError(Exception):
                        def __init__(self, status, reason, body):
                            self.status = status
                            self.reason = reason
                            self.body = body
                            super().__init__(f"{status}, message='{reason}', url='{url}'")
                    
                    raise KrokiError(response.status, response.reason, error_body)
                
                return await response.read()