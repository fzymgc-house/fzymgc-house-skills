#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx", "pyyaml"]
# ///
"""
Terraform MCP Gateway Script

Invokes Terraform MCP server tools without requiring MCP server configuration.
Reduces context overhead by not loading all MCP tool definitions.

Usage:
    terraform_mcp.py list-tools                    # List available tools
    terraform_mcp.py describe <tool>               # Describe a tool's schema
    terraform_mcp.py tool <name> '<json_args>'     # Call a raw tool

Environment Variables:
    TFE_TOKEN    - HCP Terraform API token (required)
    TFE_ORG      - Default organization name (required)
    TFE_ADDRESS  - TFC/TFE URL (default: https://app.terraform.io)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

# Configuration
DEFAULT_TFE_ADDRESS = "https://app.terraform.io"
DOCKER_IMAGE = "hashicorp/terraform-mcp-server:0.3.3"
SESSION_DIR = Path.home() / ".cache" / "terraform-mcp"
SESSION_TIMEOUT = 300  # 5 minutes
POLL_INTERVAL = 5  # seconds


class MCPStdioClient:
    """MCP client communicating via stdio with Docker container."""

    def __init__(self, proc: subprocess.Popen):
        self.proc = proc
        self.request_id = 0
        self._initialized = False

    def _send(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send JSON-RPC request and receive response."""
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {},
        }

        try:
            line = json.dumps(request) + "\n"
            self.proc.stdin.write(line.encode())
            self.proc.stdin.flush()

            response_line = self.proc.stdout.readline()
            if not response_line:
                return {"error": {"message": "No response from server"}}

            return json.loads(response_line)
        except (BrokenPipeError, json.JSONDecodeError) as e:
            return {"error": {"message": str(e)}}

    def initialize(self) -> dict[str, Any]:
        """Initialize the MCP session."""
        if self._initialized:
            return {"success": True}

        result = self._send("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "terraform-mcp-gateway", "version": "1.0.0"},
        })

        if "error" not in result:
            self._initialized = True
            # Send initialized notification
            self._send("notifications/initialized", {})

        return result

    def list_tools(self) -> dict[str, Any]:
        """List all available tools."""
        self.initialize()
        result = self._send("tools/list")

        if "error" in result:
            return {"success": False, "error": result["error"].get("message", str(result["error"]))}

        if "result" in result and "tools" in result["result"]:
            tool_names = [t["name"] for t in result["result"]["tools"]]
            return {"success": True, "tools": sorted(tool_names)}

        return {"success": False, "error": f"Unexpected response: {result}"}

    def describe_tool(self, tool_name: str) -> dict[str, Any]:
        """Get schema for a specific tool."""
        self.initialize()
        result = self._send("tools/list")

        if "error" in result:
            return {"success": False, "error": result["error"].get("message", str(result["error"]))}

        if "result" in result and "tools" in result["result"]:
            for tool in result["result"]["tools"]:
                if tool["name"] == tool_name:
                    return {
                        "success": True,
                        "tool": {
                            "name": tool["name"],
                            "description": tool.get("description", ""),
                            "inputSchema": tool.get("inputSchema", {}),
                        },
                    }

            all_tools = [t["name"] for t in result["result"]["tools"]]
            similar = [t for t in all_tools if tool_name.lower() in t.lower()]
            msg = f"Tool '{tool_name}' not found."
            if similar:
                msg += f" Similar: {', '.join(similar[:5])}"
            return {"success": False, "error": msg}

        return {"success": False, "error": f"Unexpected response: {result}"}

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool with arguments."""
        self.initialize()
        result = self._send("tools/call", {"name": tool_name, "arguments": arguments})

        if "error" in result:
            return {"success": False, "error": result["error"].get("message", str(result["error"]))}

        if "result" in result:
            return {"success": True, "result": result["result"]}

        return {"success": False, "error": f"Unexpected response: {result}"}

    def close(self):
        """Terminate the MCP server process."""
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()


class SessionManager:
    """Manage Docker container session for MCP server."""

    def __init__(self):
        self.session_dir = SESSION_DIR
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.pid_file = self.session_dir / "server.pid"
        self.proc: subprocess.Popen | None = None

    def _get_env(self) -> dict[str, str]:
        """Get environment variables for Docker container."""
        token = os.environ.get("TFE_TOKEN")
        if not token:
            raise EnvironmentError("TFE_TOKEN environment variable is required")

        address = os.environ.get("TFE_ADDRESS", DEFAULT_TFE_ADDRESS)

        return {
            "TFE_TOKEN": token,
            "TFE_ADDRESS": address,
        }

    def _spawn_container(self) -> subprocess.Popen:
        """Spawn a new Docker container."""
        env = self._get_env()

        cmd = [
            "docker", "run", "-i", "--rm",
            "-e", f"TFE_TOKEN={env['TFE_TOKEN']}",
            "-e", f"TFE_ADDRESS={env['TFE_ADDRESS']}",
            DOCKER_IMAGE,
        ]

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Save PID for session reuse (future enhancement)
        self.pid_file.write_text(str(proc.pid))

        return proc

    def get_client(self) -> MCPStdioClient:
        """Get or create MCP client."""
        # For now, always spawn fresh container
        # Session reuse can be added later
        self.proc = self._spawn_container()
        return MCPStdioClient(self.proc)

    def cleanup(self):
        """Clean up resources."""
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()

        if self.pid_file.exists():
            self.pid_file.unlink()


def unwrap_result(data: dict[str, Any]) -> Any:
    """Unwrap MCP result structure to return just the data."""
    if not data.get("success"):
        return data

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
    """Format output according to specified format."""
    if fmt == "json":
        return json.dumps(data, separators=(",", ":"))
    elif fmt == "yaml":
        return yaml.dump(data, default_flow_style=False, sort_keys=False)
    else:  # compact
        return yaml.dump(data, default_flow_style=True, sort_keys=False)


def main():
    parser = argparse.ArgumentParser(
        description="Terraform MCP Gateway - invoke Terraform tools without MCP context overhead",
    )
    parser.add_argument(
        "--format",
        choices=["json", "yaml", "compact"],
        default="yaml",
        help="Output format (default: yaml)",
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # list-tools
    subparsers.add_parser("list-tools", help="List available MCP tools")

    # describe
    describe_parser = subparsers.add_parser("describe", help="Describe a tool's schema")
    describe_parser.add_argument("name", help="Tool name")

    # tool (raw tool call)
    tool_parser = subparsers.add_parser("tool", help="Call an MCP tool directly")
    tool_parser.add_argument("name", help="Tool name")
    tool_parser.add_argument("arguments", nargs="?", default="{}", help="JSON arguments")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    session = SessionManager()

    try:
        client = session.get_client()

        if args.command == "list-tools":
            result = client.list_tools()
            if result.get("success"):
                print(format_output(result["tools"], args.format))
                sys.exit(0)
            else:
                print(f"Error: {result.get('error')}", file=sys.stderr)
                sys.exit(1)

        elif args.command == "describe":
            result = client.describe_tool(args.name)
            if result.get("success"):
                print(format_output(result["tool"], args.format))
                sys.exit(0)
            else:
                print(f"Error: {result.get('error')}", file=sys.stderr)
                sys.exit(1)

        elif args.command == "tool":
            try:
                arguments = json.loads(args.arguments)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON arguments: {e}", file=sys.stderr)
                sys.exit(1)

            result = client.call_tool(args.name, arguments)
            output = unwrap_result(result)

            if result.get("success"):
                print(format_output(output, args.format))
                sys.exit(0)
            else:
                print(f"Error: {result.get('error', 'Unknown error')}", file=sys.stderr)
                sys.exit(1)

    except EnvironmentError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        session.cleanup()


if __name__ == "__main__":
    main()
