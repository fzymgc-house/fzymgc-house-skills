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


def workflow_investigate_logs(client: MCPClient, params: dict[str, Any], fmt: str) -> int:
    """Find errors in logs for a service."""
    app = params.get("app", "")
    time_range = params.get("timeRange", "1h")
    pattern = params.get("pattern", "error")

    if not app:
        print("Error: 'app' parameter is required", file=sys.stderr)
        return 1

    # Step 1: Find Loki datasource
    ds_result = client.call_tool("list_datasources", {"type": "loki"})
    if not ds_result.get("success"):
        print(f"Error finding Loki datasource: {ds_result.get('error')}", file=sys.stderr)
        return 1

    loki_uid = None
    content = ds_result.get("result", {}).get("content", [])
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            try:
                datasources = json.loads(item["text"])
                if datasources:
                    loki_uid = datasources[0].get("uid")
                    break
            except (json.JSONDecodeError, TypeError, IndexError):
                pass

    if not loki_uid:
        print("Error: No Loki datasource found", file=sys.stderr)
        return 1

    logql = f'{{app="{app}"}}'

    # Step 2: Query stats
    stats_result = client.call_tool("query_loki_stats", {
        "datasourceUid": loki_uid,
        "logql": logql,
        "startRfc3339": f"now-{time_range}",
    })

    stats = {"streams": 0, "entries": 0, "bytes": 0}
    if stats_result.get("success"):
        content = stats_result.get("result", {}).get("content", [])
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                try:
                    stats = json.loads(item["text"])
                except (json.JSONDecodeError, TypeError):
                    pass

    # Step 3: Query logs with error pattern
    error_logql = f'{{app="{app}"}} |= "{pattern}"'
    logs_result = client.call_tool("query_loki_logs", {
        "datasourceUid": loki_uid,
        "logql": error_logql,
        "limit": 20,
        "startRfc3339": f"now-{time_range}",
    })

    errors = []
    if logs_result.get("success"):
        content = logs_result.get("result", {}).get("content", [])
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                try:
                    log_entries = json.loads(item["text"])
                    if isinstance(log_entries, list):
                        errors = [f"{e.get('timestamp', '')} {e.get('line', '')[:100]}"
                                  for e in log_entries[:5]]
                except (json.JSONDecodeError, TypeError):
                    pass

    # Build output
    output = {
        "datasource": loki_uid,
        "timeRange": f"now-{time_range} to now",
        "query": error_logql,
        "stats": stats,
        "errors": {
            "count": len(errors),
            "sample": errors,
        }
    }

    print(format_output(output, fmt))
    return 0


def workflow_investigate_metrics(client: MCPClient, params: dict[str, Any], fmt: str) -> int:
    """Check metric health for a job/service.

    Args:
        params: {"job": "...", "metric": "up", "timeRange": "1h"}
                job is optional - if omitted, queries metric without label filter
    """
    job = params.get("job", "")
    metric = params.get("metric", "up")
    time_range = params.get("timeRange", "1h")

    # Find Prometheus datasource
    ds_result = client.call_tool("list_datasources", {"type": "prometheus"})
    if not ds_result.get("success"):
        print(f"Error finding Prometheus datasource: {ds_result.get('error')}", file=sys.stderr)
        return 1

    prom_uid = None
    content = ds_result.get("result", {}).get("content", [])
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            try:
                datasources = json.loads(item["text"])
                if datasources:
                    prom_uid = datasources[0].get("uid")
                    break
            except (json.JSONDecodeError, TypeError, IndexError):
                pass

    if not prom_uid:
        print("Error: No Prometheus datasource found", file=sys.stderr)
        return 1

    # Build query
    if job:
        expr = f'{metric}{{job="{job}"}}'
    else:
        expr = metric

    # Query current value
    query_result = client.call_tool("query_prometheus", {
        "datasourceUid": prom_uid,
        "expr": expr,
        "startTime": f"now-{time_range}",
        "queryType": "instant",
    })

    value = None
    if query_result.get("success"):
        content = query_result.get("result", {}).get("content", [])
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                try:
                    result = json.loads(item["text"])
                    if result and "value" in result:
                        value = result["value"]
                except (json.JSONDecodeError, TypeError):
                    pass

    output = {
        "datasource": prom_uid,
        "query": expr,
        "timeRange": f"now-{time_range}",
        "result": value if value else "no data",
    }

    print(format_output(output, fmt))
    return 0


def workflow_quick_status(client: MCPClient, params: dict[str, Any], fmt: str) -> int:
    """Overview of system health."""
    output = {"incidents": {"active": 0}, "alerts": {"firing": []}}

    # Get active incidents
    inc_result = client.call_tool("list_incidents", {"status": "active", "limit": 10})
    if inc_result.get("success"):
        content = inc_result.get("result", {}).get("content", [])
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                try:
                    incidents = json.loads(item["text"])
                    if isinstance(incidents, list):
                        output["incidents"]["active"] = len(incidents)
                        output["incidents"]["items"] = [
                            {"title": i.get("title"), "severity": i.get("severity")}
                            for i in incidents[:5]
                        ]
                except (json.JSONDecodeError, TypeError):
                    pass

    # Get firing alerts
    alert_result = client.call_tool("list_alert_rules", {"limit": 50})
    if alert_result.get("success"):
        content = alert_result.get("result", {}).get("content", [])
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                try:
                    alerts = json.loads(item["text"])
                    if isinstance(alerts, list):
                        firing = [a for a in alerts if a.get("state") == "firing"]
                        output["alerts"]["firing"] = [
                            f"{a.get('title')} ({a.get('labels', {}).get('severity', 'unknown')})"
                            for a in firing[:10]
                        ]
                except (json.JSONDecodeError, TypeError):
                    pass

    print(format_output(output, fmt))
    return 0


def workflow_find_dashboard(client: MCPClient, params: dict[str, Any], fmt: str) -> int:
    """Search and summarize a dashboard."""
    query = params.get("query", "")
    if not query:
        print("Error: 'query' parameter is required", file=sys.stderr)
        return 1

    # Search dashboards
    search_result = client.call_tool("search_dashboards", {"query": query})
    if not search_result.get("success"):
        print(f"Error searching dashboards: {search_result.get('error')}", file=sys.stderr)
        return 1

    dashboards = []
    content = search_result.get("result", {}).get("content", [])
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            try:
                dashboards = json.loads(item["text"])
            except (json.JSONDecodeError, TypeError):
                pass

    if not dashboards:
        print(format_output({"found": 0, "message": "No dashboards found"}, fmt))
        return 0

    # Get summary of top match
    top = dashboards[0]
    summary_result = client.call_tool("get_dashboard_summary", {"uid": top.get("uid")})

    summary = {}
    if summary_result.get("success"):
        content = summary_result.get("result", {}).get("content", [])
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                try:
                    summary = json.loads(item["text"])
                except (json.JSONDecodeError, TypeError):
                    pass

    output = {
        "found": len(dashboards),
        "top_match": {
            "uid": top.get("uid"),
            "title": top.get("title"),
            "folder": top.get("folderTitle", "General"),
            "panels": summary.get("panelCount", 0),
            "types": summary.get("panelTypes", []),
            "variables": summary.get("variables", []),
            "url": top.get("url", ""),
        }
    }

    print(format_output(output, fmt))
    return 0


def main():
    # Backward compatibility: convert old style to new style
    if len(sys.argv) > 1:
        first_arg = sys.argv[1]
        if first_arg == "--list-tools":
            sys.argv = [sys.argv[0], "list-tools"] + sys.argv[2:]
        elif first_arg == "--describe":
            sys.argv = [sys.argv[0], "describe"] + sys.argv[2:]
        elif first_arg.startswith("--"):
            pass  # Regular flag
        elif first_arg not in ["tool", "list-tools", "describe", "investigate-logs",
                                "investigate-metrics", "quick-status", "find-dashboard"]:
            # Old style: tool_name '{args}' -> tool tool_name '{args}'
            sys.argv = [sys.argv[0], "tool"] + sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Grafana MCP Gateway - invoke Grafana tools without MCP context overhead",
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("GRAFANA_MCP_URL", DEFAULT_MCP_URL),
        help=f"MCP server URL (default: {DEFAULT_MCP_URL})",
    )
    parser.add_argument(
        "--format",
        choices=["json", "yaml", "compact"],
        default="yaml",
        help="Output format (default: yaml)",
    )
    parser.add_argument(
        "--brief",
        action="store_true",
        help="Return only essential fields",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Tool operations
    tool_parser = subparsers.add_parser("tool", help="Call an MCP tool")
    tool_parser.add_argument("name", help="Tool name")
    tool_parser.add_argument("arguments", nargs="?", default="{}", help="JSON arguments")

    # List tools
    subparsers.add_parser("list-tools", help="List available MCP tools")

    # Describe tool
    describe_parser = subparsers.add_parser("describe", help="Describe a tool's schema")
    describe_parser.add_argument("name", help="Tool name")

    # Workflows (to be implemented in Task 2.2 and 2.3)
    investigate_logs = subparsers.add_parser("investigate-logs", help="Find errors in logs")
    investigate_logs.add_argument("params", nargs="?", default="{}", help='{"app":"...","timeRange":"1h"}')

    investigate_metrics = subparsers.add_parser("investigate-metrics", help="Check metric health")
    investigate_metrics.add_argument("params", nargs="?", default="{}", help='{"job":"...","metric":"..."}')

    quick_status = subparsers.add_parser("quick-status", help="System health overview")
    quick_status.add_argument("params", nargs="?", default="{}", help="Optional filters")

    find_dashboard = subparsers.add_parser("find-dashboard", help="Search and summarize dashboard")
    find_dashboard.add_argument("params", nargs="?", default="{}", help='{"query":"..."}')

    args = parser.parse_args()
    client = MCPClient(args.url)

    try:
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
            if args.brief:
                output = apply_brief_filter(output, args.name)

            if result.get("success"):
                print(format_output(output, args.format))
                sys.exit(0)
            else:
                print(f"Error: {result.get('error', 'Unknown error')}", file=sys.stderr)
                sys.exit(1)

        elif args.command == "investigate-logs":
            try:
                params = json.loads(args.params)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON params: {e}", file=sys.stderr)
                sys.exit(1)
            sys.exit(workflow_investigate_logs(client, params, args.format))

        elif args.command == "investigate-metrics":
            try:
                params = json.loads(args.params)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON params: {e}", file=sys.stderr)
                sys.exit(1)
            sys.exit(workflow_investigate_metrics(client, params, args.format))

        elif args.command == "quick-status":
            try:
                params = json.loads(args.params)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON params: {e}", file=sys.stderr)
                sys.exit(1)
            sys.exit(workflow_quick_status(client, params, args.format))

        elif args.command == "find-dashboard":
            try:
                params = json.loads(args.params)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON params: {e}", file=sys.stderr)
                sys.exit(1)
            sys.exit(workflow_find_dashboard(client, params, args.format))

        else:
            parser.print_help()
            sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
