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
import tempfile
from pathlib import Path
from typing import Any

import httpx
import yaml

# Configuration
DEFAULT_TFE_ADDRESS = "https://app.terraform.io"
DOCKER_IMAGE = "hashicorp/terraform-mcp-server:0.3.3"
SESSION_DIR = Path.home() / ".cache" / "terraform-mcp"
SESSION_TIMEOUT = 300  # 5 minutes


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
        self.proc: subprocess.Popen | None = None
        self._client: MCPStdioClient | None = None
        self._env_file_path: str | None = None

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

        # Write env vars to temp file to avoid exposing token in process list
        env_file = tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False)
        env_file.write(f"TFE_TOKEN={env['TFE_TOKEN']}\n")
        env_file.write(f"TFE_ADDRESS={env['TFE_ADDRESS']}\n")
        env_file.close()
        self._env_file_path = env_file.name

        cmd = [
            "docker", "run", "-i", "--rm",
            "--env-file", self._env_file_path,
            DOCKER_IMAGE,
        ]

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        return proc

    def get_client(self) -> MCPStdioClient:
        """Get or create MCP client."""
        # For now, always spawn fresh container
        # TODO: Session reuse can be added later
        self.proc = self._spawn_container()
        self._client = MCPStdioClient(self.proc)
        return self._client

    def cleanup(self):
        """Clean up resources."""
        # Close MCP client first
        if self._client:
            self._client.close()
            self._client = None

        # Terminate container process (redundant but safe)
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None

        # Remove temp env file
        if self._env_file_path and os.path.exists(self._env_file_path):
            os.unlink(self._env_file_path)
            self._env_file_path = None


class HCPTerraformClient:
    """Direct HCP Terraform API client for operations not exposed via MCP."""

    def __init__(self, token: str, address: str = DEFAULT_TFE_ADDRESS):
        self.client = httpx.Client(
            base_url=address.rstrip("/"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/vnd.api+json",
            },
            timeout=30.0,
        )

    def get_plan_logs(self, plan_id: str) -> dict[str, Any]:
        """Fetch plan logs from HCP Terraform API."""
        try:
            resp = self.client.get(f"/api/v2/plans/{plan_id}")
            resp.raise_for_status()
            plan_data = resp.json()

            log_url = plan_data.get("data", {}).get("attributes", {}).get("log-read-url")
            if not log_url:
                return {"success": False, "error": "No log URL available"}

            log_resp = httpx.get(log_url, timeout=30.0)
            log_resp.raise_for_status()
            return {"success": True, "logs": log_resp.text}
        except httpx.HTTPStatusError as e:
            return {"success": False, "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_apply_logs(self, apply_id: str) -> dict[str, Any]:
        """Fetch apply logs from HCP Terraform API."""
        try:
            resp = self.client.get(f"/api/v2/applies/{apply_id}")
            resp.raise_for_status()
            apply_data = resp.json()

            log_url = apply_data.get("data", {}).get("attributes", {}).get("log-read-url")
            if not log_url:
                return {"success": False, "error": "No log URL available"}

            log_resp = httpx.get(log_url, timeout=30.0)
            log_resp.raise_for_status()
            return {"success": True, "logs": log_resp.text}
        except httpx.HTTPStatusError as e:
            return {"success": False, "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_run(self, run_id: str) -> dict[str, Any]:
        """Get run details including plan/apply IDs."""
        try:
            resp = self.client.get(f"/api/v2/runs/{run_id}")
            resp.raise_for_status()
            return {"success": True, "data": resp.json()}
        except httpx.HTTPStatusError as e:
            return {"success": False, "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def close(self):
        """Close the HTTP client."""
        self.client.close()


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


def get_default_org() -> str:
    """Get default organization from environment."""
    org = os.environ.get("TFE_ORG")
    if not org:
        raise EnvironmentError("TFE_ORG environment variable is required")
    return org


def _truncate_message(msg: str, max_len: int) -> str:
    """Truncate message with ellipsis if too long."""
    if len(msg) <= max_len:
        return msg
    return msg[:max_len - 3] + "..."


def workflow_workspace_status(client: MCPStdioClient, args: argparse.Namespace, fmt: str) -> int:
    """Show workspace status overview."""
    org = get_default_org()
    workspace_name = getattr(args, "workspace", None)

    if workspace_name:
        # Single workspace detail
        result = client.call_tool("get_workspace_details", {
            "terraform_org_name": org,
            "workspace_name": workspace_name,
        })

        if not result.get("success"):
            print(f"Error: {result.get('error')}", file=sys.stderr)
            return 1

        data = unwrap_result(result)
        if not isinstance(data, dict):
            print("Error: Unexpected response format", file=sys.stderr)
            return 1

        # Extract key fields
        output = {
            "workspace": workspace_name,
            "organization": org,
            "workspace_id": data.get("id", ""),
            "terraform_version": data.get("attributes", {}).get("terraform-version", ""),
            "execution_mode": data.get("attributes", {}).get("execution-mode", ""),
            "auto_apply": data.get("attributes", {}).get("auto-apply", False),
            "working_directory": data.get("attributes", {}).get("working-directory", ""),
            "vcs_repo": data.get("attributes", {}).get("vcs-repo", {}),
            "updated_at": data.get("attributes", {}).get("updated-at", ""),
        }

        print(format_output(output, fmt))
        return 0

    else:
        # List all workspaces
        result = client.call_tool("list_workspaces", {
            "terraform_org_name": org,
        })

        if not result.get("success"):
            print(f"Error: {result.get('error')}", file=sys.stderr)
            return 1

        data = unwrap_result(result)

        # Validate data type before processing
        if not isinstance(data, (dict, list)):
            print(f"Error: Unexpected response format: {type(data).__name__}", file=sys.stderr)
            return 1

        # Handle various response structures from MCP
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and "data" in data:
            items = data["data"] if isinstance(data["data"], list) else []
        elif isinstance(data, dict) and "items" in data:
            items = data["items"] if isinstance(data["items"], list) else []
        elif isinstance(data, dict):
            items = [data]  # Single workspace response
        else:
            print("Error: Could not extract workspace list from response", file=sys.stderr)
            return 1

        # Format as brief list
        workspaces = []
        for ws in items:
            attrs = ws.get("attributes", {}) if isinstance(ws, dict) else {}
            workspaces.append({
                "name": attrs.get("name", ws.get("name", "")),
                "id": ws.get("id", ""),
                "terraform_version": attrs.get("terraform-version", ""),
                "updated_at": attrs.get("updated-at", ""),
            })

        output = {
            "organization": org,
            "count": len(workspaces),
            "workspaces": workspaces,
        }

        print(format_output(output, fmt))
        return 0


def workflow_list_runs(client: MCPStdioClient, args: argparse.Namespace, fmt: str) -> int:
    """List recent runs for a workspace."""
    org = get_default_org()
    workspace = getattr(args, "workspace", None)
    if not workspace:
        print("Error: workspace argument is required", file=sys.stderr)
        return 1
    limit = getattr(args, "limit", 10)
    status_filter = getattr(args, "status", None)

    params: dict[str, Any] = {
        "terraform_org_name": org,
        "workspace_name": workspace,
        "pageSize": limit,
    }

    if status_filter:
        params["status"] = [status_filter]

    result = client.call_tool("list_runs", params)

    if not result.get("success"):
        print(f"Error: {result.get('error')}", file=sys.stderr)
        return 1

    data = unwrap_result(result)

    # Validate data type
    if not isinstance(data, (dict, list)):
        print(f"Error: Unexpected response format: {type(data).__name__}", file=sys.stderr)
        return 1

    # Handle various response structures
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and "data" in data:
        items = data["data"] if isinstance(data["data"], list) else []
    elif isinstance(data, dict) and "items" in data:
        items = data["items"] if isinstance(data["items"], list) else []
    else:
        items = [data] if data else []

    runs = []
    for run in items:
        attrs = run.get("attributes", {}) if isinstance(run, dict) else {}
        runs.append({
            "id": run.get("id", ""),
            "status": attrs.get("status", ""),
            "message": _truncate_message(attrs.get("message", "") or "", 80),
            "created_at": attrs.get("created-at", ""),
            "plan_only": attrs.get("plan-only", False),
            "is_destroy": attrs.get("is-destroy", False),
        })

    output = {
        "workspace": workspace,
        "organization": org,
        "count": len(runs),
        "runs": runs,
    }

    print(format_output(output, fmt))
    return 0


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

    # workspace-status
    ws_parser = subparsers.add_parser("workspace-status", help="Show workspace status")
    ws_parser.add_argument("workspace", nargs="?", help="Workspace name (optional, lists all if omitted)")

    # list-runs
    runs_parser = subparsers.add_parser("list-runs", help="List recent runs for a workspace")
    runs_parser.add_argument("workspace", help="Workspace name")
    runs_parser.add_argument("--limit", type=int, default=10, help="Number of runs (default: 10)")
    runs_parser.add_argument("--status", help="Filter by status (e.g., applied, errored, planning)")

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

        elif args.command == "workspace-status":
            sys.exit(workflow_workspace_status(client, args, args.format))

        elif args.command == "list-runs":
            sys.exit(workflow_list_runs(client, args, args.format))

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
