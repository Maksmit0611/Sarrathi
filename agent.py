#!/usr/bin/env python3
"""
agent.py — Sarathi, the agent. This is the thing you run.

    python3 agent.py                          interactive session (REPL)
    python3 agent.py "research a tiffin service in Bengaluru, no budget"
    python3 agent.py --watch                  run queued tasks and exit (for cron)
    python3 agent.py --mcp                    connect MCP servers as extra tools
    python3 agent.py --tools                  show everything the agent can do
    python3 agent.py --memory                 show what it remembers about you
    python3 agent.py --queue "..."            add a task for the next --watch run

Why this is an agent and not an app:

  * it runs as a process on your machine, not a page someone visits
  * it has persistent memory across sessions (~/.sarrathi)
  * it has tools it can actually call - files, shell, web, the Shodh engine, MCP servers
  * it loops: think, act, observe, think again, until the job is done
  * it can run unattended on a schedule

Add a free API key to give it reasoning; without one it still does real work.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from idea_oracle.brain import get_brain, describe_providers
from sarrathi import tools as toolkit
from sarrathi.loop import Agent, HELP_TEXT
from sarrathi.memory import AgentMemory

BANNER = r"""
   ▄▄▄▄▄▄▄   Sarathi  सारथि
  █ ☸     █  the charioteer — your research agent
  █  ▄▄▄  █
  █  ███  █  Sarathi Labs · engine: Shodh · delivers: Arthabodh
   ▀▀▀▀▀▀▀
"""


def resolve_paths(args) -> None:
    """
    One flag should be enough. `--home DIR` means "the agent lives here", so that is
    also where it works (reports, skills, notes). Run without --home and it lives in
    ~/.sarrathi but works in the directory you launched it from.
    """
    if args.workspace:
        os.environ["SARRATHI_WORKSPACE"] = str(Path(args.workspace).expanduser().resolve())
    elif args.home and not os.environ.get("SARRATHI_WORKSPACE"):
        os.environ["SARRATHI_WORKSPACE"] = str(Path(args.home).expanduser().resolve())
    toolkit.WORKSPACE = Path(os.environ.get("SARRATHI_WORKSPACE", Path.cwd())).resolve()


def build_agent(args) -> Agent:
    brain = get_brain(prefer_offline=args.offline)
    agent = Agent(brain=brain, home=args.home, verbose=not args.quiet)

    if args.mcp or args.mcp_list:
        from sarrathi import mcp_bridge
        try:
            servers = mcp_bridge.connect_all()
            n = mcp_bridge.register(servers)
            print(f"  {n} MCP tools registered from {len(servers)} server(s)\n")
            if args.mcp_list:
                print(mcp_bridge.describe(servers))
                sys.exit(0)
        except Exception as exc:  # noqa: BLE001
            print(f"  MCP unavailable: {exc}", file=sys.stderr)
    return agent


def print_status(agent: Agent, args) -> None:
    stats = agent.memory.stats()
    brain = "offline (no model — tools still work)" if agent.offline else agent.brain.label
    print(BANNER)
    print(f"  brain      : {brain}")
    print(f"  tools      : {len(toolkit.REGISTRY)}")
    print(f"  memory     : {stats['facts']} facts · {stats['sessions']} sessions · {stats['home']}")
    print(f"  workspace  : {toolkit.WORKSPACE}")
    print(f"  identity   : {agent.identity.home / 'identity'}")
    print()
    if agent.offline:
        print("  No LLM key found. I'll route requests with rules — research, memory, files and")
        print("  shell all still work. Add GROQ_API_KEY (free) for full reasoning.")
        print()
    print("  Type /help for commands, or just describe what you need. ctrl-D to exit.\n")


def repl(agent: Agent, args) -> int:
    print_status(agent, args)
    history: list[dict] = []
    while True:
        try:
            line = input("you › ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nbye — memory saved to", agent.memory.home)
            return 0
        if not line:
            continue
        if line.lower() in ("exit", "quit", "q", "/exit"):
            print("bye — memory saved to", agent.memory.home)
            return 0

        turn = agent.turn(line, history=history)
        print(f"\nsarathi › {turn.answer}\n")
        if turn.steps:
            tools_used = ", ".join(s.tool for s in turn.steps)
            print(f"  [{len(turn.steps)} tool call(s): {tools_used} · {turn.elapsed_ms}ms · {turn.stopped_reason}]\n")
        history.append({"role": "user", "content": line})
        history.append({"role": "assistant", "content": turn.answer[:1200]})
        history = history[-8:]


def run_once(agent: Agent, goal: str, as_json: bool = False) -> int:
    turn = agent.turn(goal)
    if as_json:
        print(json.dumps({"goal": turn.goal, "answer": turn.answer, "brain": turn.brain,
                          "stopped_reason": turn.stopped_reason, "elapsed_ms": turn.elapsed_ms,
                          "steps": [{"tool": s.tool, "args": s.arguments,
                                     "result": s.result[:500]} for s in turn.steps]}, indent=2))
    else:
        print(turn.answer)
        if turn.steps:
            print("\n--- what I did ---")
            for s in turn.steps:
                print(f"  {s.n}. {s.tool}({json.dumps(s.arguments)[:90]}) → {s.result.splitlines()[0][:90]}")
    return 0


def watch(agent: Agent, args) -> int:
    """
    Run queued goals, then exit. This is how you put an agent on a schedule:

        # crontab -e
        0 8 * * 1  cd /path/to/sarathi-labs && python3 agent.py --watch >> ~/.sarrathi/logs/cron.log 2>&1

    The agent then works for you while you are not at the keyboard - which is the
    thing an app can never do.
    """
    queue_file = agent.memory.home / "queue.jsonl"
    if not queue_file.exists():
        print(f"Nothing queued. Add one with:  python3 agent.py --queue \"...\"")
        return 0
    lines = [l for l in queue_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not lines:
        print("Queue is empty.")
        return 0
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{stamp}] running {len(lines)} queued task(s)")
    results = []
    for i, line in enumerate(lines, 1):
        try:
            goal = json.loads(line).get("goal", line)
        except json.JSONDecodeError:
            goal = line
        print(f"\n[{i}/{len(lines)}] {goal}")
        turn = agent.turn(goal)
        print(turn.answer[:1500])
        results.append({"goal": goal, "answer": turn.answer, "at": stamp})
    # archive the run
    out = agent.memory.logs_dir / f"watch-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    queue_file.write_text("", encoding="utf-8")
    print(f"\nDone. Run archived to {out}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Sarathi — a business-research agent that runs on your machine, remembers, and acts.",
        epilog="Example:  python3 agent.py \"research a home tiffin service in Bengaluru with no budget\"")
    ap.add_argument("goal", nargs="*", help="One-shot task. Omit for an interactive session.")
    ap.add_argument("--home", help="Where the agent lives and works (default ~/.sarrathi)")
    ap.add_argument("--workspace", help="Directory for files/reports (default: same as --home, or cwd)")
    ap.add_argument("--offline", action="store_true", help="Force no-LLM mode (tools only).")
    ap.add_argument("--quiet", action="store_true", help="Hide tool-call trace.")
    ap.add_argument("--json", action="store_true", help="Machine-readable output.")
    ap.add_argument("--tools", action="store_true", help="List every tool the agent can call.")
    ap.add_argument("--memory", action="store_true", help="Show what the agent remembers.")
    ap.add_argument("--identity", action="store_true", help="Show the agent's identity files.")
    ap.add_argument("--providers", action="store_true", help="Show available free LLM brains.")
    ap.add_argument("--mcp", action="store_true", help="Connect MCP servers from mcp.json.")
    ap.add_argument("--mcp-list", action="store_true", help="Connect MCP servers and list their tools.")
    ap.add_argument("--queue", metavar="GOAL", help="Add a goal to the queue for the next --watch run.")
    ap.add_argument("--watch", action="store_true", help="Run the queue once and exit (for cron).")
    args = ap.parse_args()
    resolve_paths(args)

    if args.providers:
        print(describe_providers())
        return 0

    if args.queue:
        mem = AgentMemory(args.home)
        q = mem.home / "queue.jsonl"
        with open(q, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"goal": args.queue, "added": datetime.now().isoformat(timespec="seconds")}) + "\n")
        print(f"Queued. It will run on the next: python3 agent.py --watch")
        return 0

    agent = build_agent(args)

    if args.tools:
        print(f"{len(toolkit.REGISTRY)} tools:\n")
        print(toolkit.catalogue())
        return 0
    if args.memory:
        print(json.dumps(agent.memory.stats(), indent=2))
        print("\nrecent:")
        for m in agent.memory.recent(limit=15):
            print(f"  [{m.kind}] {m.ts[:10]} — {m.text[:100]}")
        return 0
    if args.identity:
        print(f"--- IDENTITY ---\n{agent.identity.identity}\n")
        print(f"--- SOUL ---\n{agent.identity.soul}\n")
        print(f"--- USER ---\n{agent.identity.user}")
        return 0
    if args.watch:
        return watch(agent, args)

    if args.goal:
        return run_once(agent, " ".join(args.goal), as_json=args.json)

    return repl(agent, args)


if __name__ == "__main__":
    raise SystemExit(main())
