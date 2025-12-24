#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx", "pyyaml"]
# ///
"""
Grafana MCP Gateway Script

Invokes Grafana MCP server tools without requiring MCP server configuration.
Reduces context overhead by not loading all MCP tool definitions.

Usage:
    grafana_mcp.py --list-tools              # List available tools
    grafana_mcp.py --describe <tool>         # Describe a tool's schema
    grafana_mcp.py <tool> '<json_args>'      # Call a tool

Examples:
    grafana_mcp.py --list-tools
    grafana_mcp.py --describe query_prometheus
    grafana_mcp.py list_datasources '{}'
    uv run grafana_mcp.py query_prometheus '{"datasourceUid":"x","expr":"up","startTime":"now-1h","queryType":"instant"}'
"""

import argparse
import json
import os
import sys
from typing import Any

import httpx

DEFAULT_MCP_URL = "https://mcp.grafana.fzymgc.house/mcp"
TIMEOUT = 30.0


class MCPClient:
    """MCP client with session management for streamable HTTP transport."""

    def __init__(self, url: str):
        self.url = url
        self.session_id: str | None = None
        self.request_id = 0
        self.client = httpx.Client(timeout=TIMEOUT)

    def _next_id(self) -> int:
        self.request_id += 1
        return self.request_id

    def _request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send a JSON-RPC 2.0 request to the MCP server."""
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params or {},
        }

        headers = {"Content-Type": "application/json"}
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id

        try:
            response = self.client.post(self.url, json=payload, headers=headers)

            # Capture session ID from response headers
            if "Mcp-Session-Id" in response.headers:
                self.session_id = response.headers["Mcp-Session-Id"]

            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            return {"error": {"message": f"Connection failed: {e}"}}
        except httpx.HTTPStatusError as e:
            return {"error": {"message": f"HTTP error {e.response.status_code}: {e.response.text}"}}
        except httpx.TimeoutException:
            return {"error": {"message": f"Request timed out after {TIMEOUT}s"}}
        except json.JSONDecodeError as e:
            return {"error": {"message": f"Invalid JSON response: {e}"}}

    def initialize(self) -> dict[str, Any]:
        """Initialize the MCP session."""
        return self._request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "grafana-mcp-gateway",
                "version": "1.0.0"
            }
        })

    def list_tools(self) -> dict[str, Any]:
        """List all available tools from the MCP server."""
        # Ensure session is initialized
        if not self.session_id:
            init_result = self.initialize()
            if "error" in init_result:
                return {"success": False, "error": init_result["error"]["message"]}

        result = self._request("tools/list")

        if "error" in result:
            return {"success": False, "error": result["error"]["message"]}

        if "result" in result and "tools" in result["result"]:
            tool_names = [t["name"] for t in result["result"]["tools"]]
            return {"success": True, "tools": sorted(tool_names)}

        return {"success": False, "error": f"Unexpected response format: {result}"}

    def describe_tool(self, tool_name: str) -> dict[str, Any]:
        """Get the schema and description for a specific tool."""
        # Ensure session is initialized
        if not self.session_id:
            init_result = self.initialize()
            if "error" in init_result:
                return {"success": False, "error": init_result["error"]["message"]}

        result = self._request("tools/list")

        if "error" in result:
            return {"success": False, "error": result["error"]["message"]}

        if "result" in result and "tools" in result["result"]:
            for tool in result["result"]["tools"]:
                if tool["name"] == tool_name:
                    return {
                        "success": True,
                        "tool": {
                            "name": tool["name"],
                            "description": tool.get("description", ""),
                            "inputSchema": tool.get("inputSchema", {}),
                        }
                    }

            # Tool not found - suggest similar names
            all_tools = [t["name"] for t in result["result"]["tools"]]
            similar = [t for t in all_tools if tool_name.lower() in t.lower()]
            msg = f"Tool '{tool_name}' not found."
            if similar:
                msg += f" Similar tools: {', '.join(similar[:5])}"
            else:
                msg += " Use --list-tools to see available tools."
            return {"success": False, "error": msg}

        return {"success": False, "error": f"Unexpected response format: {result}"}

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool with the given arguments."""
        # Ensure session is initialized
        if not self.session_id:
            init_result = self.initialize()
            if "error" in init_result:
                return {"success": False, "error": init_result["error"]["message"]}

        result = self._request("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })

        if "error" in result:
            return {"success": False, "error": result["error"]["message"]}

        if "result" in result:
            return {"success": True, "result": result["result"]}

        return {"success": False, "error": f"Unexpected response format: {result}"}

    def close(self):
        """Close the HTTP client."""
        self.client.close()


def main():
    parser = argparse.ArgumentParser(
        description="Grafana MCP Gateway - invoke Grafana tools without MCP context overhead",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("GRAFANA_MCP_URL", DEFAULT_MCP_URL),
        help=f"MCP server URL (default: {DEFAULT_MCP_URL}, or GRAFANA_MCP_URL env var)",
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="List all available tools",
    )
    parser.add_argument(
        "--describe",
        metavar="TOOL",
        help="Describe a specific tool's schema and parameters",
    )
    parser.add_argument(
        "tool",
        nargs="?",
        help="Tool name to call",
    )
    parser.add_argument(
        "arguments",
        nargs="?",
        default="{}",
        help="JSON arguments for the tool (default: {})",
    )

    args = parser.parse_args()
    client = MCPClient(args.url)

    try:
        # Handle --list-tools
        if args.list_tools:
            result = client.list_tools()
            print(json.dumps(result, indent=2))
            sys.exit(0 if result["success"] else 1)

        # Handle --describe
        if args.describe:
            result = client.describe_tool(args.describe)
            print(json.dumps(result, indent=2))
            sys.exit(0 if result["success"] else 1)

        # Handle tool call
        if args.tool:
            try:
                arguments = json.loads(args.arguments)
            except json.JSONDecodeError as e:
                result = {"success": False, "error": f"Invalid JSON arguments: {e}"}
                print(json.dumps(result, indent=2))
                sys.exit(1)

            result = client.call_tool(args.tool, arguments)
            print(json.dumps(result, indent=2))
            sys.exit(0 if result["success"] else 1)

        # No action specified
        parser.print_help()
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
