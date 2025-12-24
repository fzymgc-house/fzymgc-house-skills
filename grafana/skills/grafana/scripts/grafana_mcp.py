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
import yaml

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


# Field filters for --brief mode (tool_name -> list of fields to keep)
BRIEF_FILTERS: dict[str, list[str]] = {
    "list_datasources": ["uid", "name", "type"],
    "search_dashboards": ["uid", "title", "folderTitle", "tags"],
    "list_alert_rules": ["uid", "title", "state", "labels"],
    "list_incidents": ["id", "title", "status", "severity"],
    "list_oncall_schedules": ["id", "name", "teamId"],
    "list_contact_points": ["uid", "name", "type"],
}


def apply_brief_filter(data: Any, tool_name: str) -> Any:
    """Apply brief filter to reduce output fields (expects unwrapped data)."""
    if tool_name not in BRIEF_FILTERS:
        return data

    fields = BRIEF_FILTERS[tool_name]

    # Handle list of objects
    if isinstance(data, list):
        return [{k: v for k, v in obj.items() if k in fields} for obj in data if isinstance(obj, dict)]

    # Handle dict with "items" key
    if isinstance(data, dict) and "items" in data:
        filtered_items = [{k: v for k, v in obj.items() if k in fields} for obj in data["items"] if isinstance(obj, dict)]
        return {**data, "items": filtered_items}

    return data


def unwrap_result(data: dict[str, Any]) -> Any:
    """Unwrap MCP result structure to return just the data."""
    if not data.get("success"):
        return data  # Keep error structure

    result = data.get("result", {})

    # Handle MCP content wrapper: {"content": [{"type": "text", "text": "..."}]}
    if "content" in result and isinstance(result["content"], list):
        texts = []
        for item in result["content"]:
            if isinstance(item, dict) and item.get("type") == "text" and "text" in item:
                try:
                    texts.append(json.loads(item["text"]))
                except json.JSONDecodeError:
                    texts.append(item["text"])

        if len(texts) == 1:
            return texts[0]
        return texts

    return result


def format_output(data: Any, fmt: str) -> str:
    """Format output data according to specified format."""
    if fmt == "json":
        return json.dumps(data, separators=(",", ":"))
    elif fmt == "yaml":
        return yaml.dump(data, default_flow_style=False, sort_keys=False)
    else:  # compact - will be enhanced per-tool later
        return yaml.dump(data, default_flow_style=False, sort_keys=False)


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
        "--format",
        choices=["json", "yaml", "compact"],
        default="yaml",
        help="Output format: json (compact), yaml (default), compact (minimal)",
    )
    parser.add_argument(
        "--brief",
        action="store_true",
        help="Return only essential fields (tool-specific filtering)",
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
            if result.get("success"):
                print(format_output(result["tools"], args.format))
                sys.exit(0)
            else:
                print(f"Error: {result.get('error')}", file=sys.stderr)
                sys.exit(1)

        # Handle --describe
        if args.describe:
            result = client.describe_tool(args.describe)
            if result.get("success"):
                print(format_output(result["tool"], args.format))
                sys.exit(0)
            else:
                print(f"Error: {result.get('error')}", file=sys.stderr)
                sys.exit(1)

        # Handle tool call
        if args.tool:
            try:
                arguments = json.loads(args.arguments)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON arguments: {e}", file=sys.stderr)
                sys.exit(1)

            result = client.call_tool(args.tool, arguments)
            if result.get("success"):
                output = unwrap_result(result)
                if args.brief:
                    output = apply_brief_filter(output, args.tool)
                print(format_output(output, args.format))
                sys.exit(0)
            else:
                print(f"Error: {result.get('error', 'Unknown error')}", file=sys.stderr)
                sys.exit(1)

        # No action specified
        parser.print_help()
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
