"""
MCP (Model Context Protocol) Client Interface.

Provides an asynchronous client that connects to a local MCP server subprocess via
stdio transport. Discovers available tools dynamically and adapts their schemas into
the tool format expected by the Ollama API.
"""

import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClient:
    """Connect to the local MCP server and expose its tools to Ollama."""

    def __init__(self) -> None:
        self.session: ClientSession | None = None
        self.ollama_tools: list[dict[str, Any]] = []
        self._exit_stack = AsyncExitStack()

    async def connect(self, server_path: Path) -> list[str]:
        """Start the stdio MCP server subprocess and discover available tools.

        Args:
            server_path: Path to the Python script implementing the MCP server.

        Returns:
            A list of discovered tool names.
        """
        if not server_path.exists():
            raise FileNotFoundError(
                f"MCP server was not found at: {server_path}"
            )

        # Launch the MCP server as a Python subprocess communicating over standard I/O
        server_parameters = StdioServerParameters(
            command=sys.executable,
            args=[str(server_path)],
        )

        read_stream, write_stream = await self._exit_stack.enter_async_context(
            stdio_client(server_parameters)
        )

        self.session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )

        await self.session.initialize()

        tools_response = await self.session.list_tools()

        # Adapt MCP tool specifications (JSON Schema) into Ollama's expected function format
        self.ollama_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema,
                },
            }
            for tool in tools_response.tools
        ]

        return [tool.name for tool in tools_response.tools]

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> str:
        """Execute an MCP tool and format the response text for the LLM.

        Args:
            tool_name: The identifier of the MCP tool to execute.
            arguments: Key-value parameters required by the tool.

        Returns:
            The string result or formatted error message produced by the tool.
        """
        if self.session is None:
            raise RuntimeError("The MCP client is not connected.")

        try:
            result = await self.session.call_tool(
                tool_name,
                arguments,
            )
        except Exception as error:
            # Catch protocol and transport failures so the LLM can explain errors gracefully
            return f"Tool execution failed: {error}"

        # Extract text payloads from response content blocks
        text_parts: list[str] = []

        for content in result.content:
            text = getattr(content, "text", None)
            if text is not None:
                text_parts.append(text)

        result_text = "\n".join(text_parts).strip()

        if result.isError:
            return (
                "MCP tool error:\n"
                f"{result_text or 'The tool failed without an error message.'}"
            )

        return result_text or "Tool completed successfully."

    async def close(self) -> None:
        """Close the MCP session and its server subprocess."""
        await self._exit_stack.aclose()
        self.session = None
        self.ollama_tools = []

    async def __aenter__(self) -> "MCPClient":
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await self.close()

