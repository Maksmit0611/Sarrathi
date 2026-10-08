"""
mcp_bridge.py — connect the agent to Model Context Protocol servers.

MCP is the standard way to give an agent new abilities without writing new code
for each one ("USB-C for AI tools", open-sourced by Anthropic in late 2024, since
adopted across the ecosystem). You configure a server once; its tools appear in
your agent like native ones.

    Your agent  ── MCP client ──►  MCP server  ──►  filesystem / GitHub / Postgres / ...

Only the standard library is used: we speak JSON-RPC 2.0 over stdio, which is the
transport nearly every MCP server supports.

Config lives in `mcp.json` next to the project, or `~/.sarrathi/mcp.json`:

    {
      "servers": {
        "memory": { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-memory"] },
        "files":  { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/me"] }
      }
    }

Then:  python3 agent.py --mcp        # start with MCP tools registered
       python3 agent.py --mcp-list   # just show what each server offers
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

PROTOCOL_VERSION = "2025-06-18"


class MCPError(RuntimeError):
    pass


class MCPServer:
    """One MCP server, spoken to over stdio with newline-delimited JSON-RPC."""

    def __init__(self, name: str, command: str, args: list[str] | None = None,
                 env: dict | None = None, timeout: int = 30):
        self.name = name
        self.timeout = timeout
        merged_env = {**os.environ, **(env or {})}
        try:
            self.proc = subprocess.Popen(
                [command, *(args or [])],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, bufsize=1, env=merged_env,
            )
        except FileNotFoundError as exc:
            raise MCPError(f"server '{name}': command not found: {command}") from exc
        self._id = 0
        self._lock = threading.Lock()
        self.tools: list[dict] = []

    # -- transport ---------------------------------------------------------
    def _send(self, method: str, params: dict | None = None, notify: bool = False) -> dict:
        with self._lock:
            self._id += 1
            msg: dict = {"jsonrpc": "2.0", "method": method}
            if params is not None:
                msg["params"] = params
            if not notify:
                msg["id"] = self._id
            try:
                self.proc.stdin.write(json.dumps(msg) + "\n")
                self.proc.stdin.flush()
            except (BrokenPipeError, ValueError) as exc:
                raise MCPError(f"server '{self.name}' closed the pipe") from exc
            if notify:
                return {}
            deadline = time.time() + self.timeout
            while time.time() < deadline:
                line = self.proc.stdout.readline()
                if not line:
                    raise MCPError(f"server '{self.name}' closed stdout")
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue                      # servers may log to stdout; skip noise
                if data.get("id") == self._id:
                    if "error" in data:
                        raise MCPError(f"{method} failed: {data['error'].get('message')}")
                    return data.get("result", {})
            raise MCPError(f"server '{self.name}': timeout on {method}")

    # -- lifecycle ---------------------------------------------------------
    def initialize(self) -> dict:
        result = self._send("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"roots": {"listChanged": False}, "sampling": {}},
            "clientInfo": {"name": "sarathi", "version": "0.3.0"},
        })
        self._send("notifications/initialized", {}, notify=True)
        return result

    def list_tools(self) -> list[dict]:
        self.tools = self._send("tools/list", {}).get("tools", [])
        return self.tools

    def call_tool(self, tool: str, arguments: dict) -> str:
        result = self._send("tools/call", {"name": tool, "arguments": arguments})
        parts: list[str] = []
        for block in result.get("content", []):
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                else:
                    parts.append(json.dumps(block))
        if result.get("isError"):
            return "error: " + ("\n".join(parts) or "tool reported failure")
        return "\n".join(parts) or "(no content)"

    def close(self) -> None:
        for stream in (self.proc.stdin, self.proc.stdout):
            try:
                stream and stream.close()
            except Exception:  # noqa: BLE001
                pass
        try:
            self.proc.terminate()
        except Exception:  # noqa: BLE001
            pass


def load_config(path: Path | None = None) -> dict:
    candidates = [path] if path else [Path("mcp.json"), Path.home() / ".sarrathi" / "mcp.json"]
    for c in candidates:
        if c and Path(c).exists():
            try:
                return json.loads(Path(c).read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise MCPError(f"mcp.json is not valid JSON: {exc}") from exc
    return {}


def connect_all(config: dict | None = None, verbose: bool = True) -> list[MCPServer]:
    cfg = config if config is not None else load_config()
    servers: list[MCPServer] = []
    for name, spec in (cfg.get("servers") or {}).items():
        try:
            srv = MCPServer(name, spec["command"], spec.get("args", []), spec.get("env"))
            info = srv.initialize()
            tools = srv.list_tools()
            servers.append(srv)
            if verbose:
                sname = info.get("serverInfo", {}).get("name", name)
                print(f"  ✓ mcp:{name} ({sname}) — {len(tools)} tools")
        except (MCPError, KeyError) as exc:
            if verbose:
                print(f"  ✗ mcp:{name} — {exc}", file=sys.stderr)
    return servers


def register(servers: list[MCPServer], prefix: str = "mcp") -> int:
    """
    Expose MCP tools through the normal tool registry, namespaced as `mcp__<server>__<tool>`
    so a native tool and a remote one can never collide.
    """
    from .tools import Tool, REGISTRY
    count = 0
    for srv in servers:
        for t in srv.tools:
            name = f"{prefix}__{srv.name}__{t['name']}"
            schema = t.get("inputSchema") or {"type": "object", "properties": {}}
            REGISTRY[name] = Tool(
                name=name,
                description=f"[{srv.name}] {t.get('description') or t['name']}",
                parameters=schema,
                fn=(lambda s=srv, tn=t["name"]: (lambda **kw: s.call_tool(tn, kw)))(),
                danger="guarded",
            )
            count += 1
    return count


def describe(servers: list[MCPServer]) -> str:
    if not servers:
        return "No MCP servers connected. Add one to mcp.json, then run with --mcp."
    lines = []
    for srv in servers:
        lines.append(f"{srv.name}: {len(srv.tools)} tools")
        for t in srv.tools:
            lines.append(f"  {t['name']:<28} {(t.get('description') or '')[:70]}")
    return "\n".join(lines)


if __name__ == "__main__":
    cfg = load_config()
    if not cfg:
        print(__doc__)
        sys.exit(0)
    servers = connect_all(cfg)
    print()
    print(describe(servers))
    for s in servers:
        s.close()
