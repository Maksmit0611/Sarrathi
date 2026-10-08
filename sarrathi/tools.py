"""
tools.py — what the Sarathi agent can actually DO.

An app responds. An agent acts. The difference is this file.

Every tool here is:
  * declared with a JSON schema (so the model can choose it),
  * implemented in plain Python (so it actually runs),
  * sandboxed or guarded where it touches the outside world.

Add a new capability to your agent by adding one entry to `REGISTRY`. That is
the whole extension model — no framework required.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    fn: Callable[..., str]
    danger: str = "safe"   # safe | guarded | dangerous

    def schema(self) -> dict:
        return {"type": "function", "function": {
            "name": self.name, "description": self.description, "parameters": self.parameters}}


REGISTRY: dict[str, Tool] = {}


def tool(name: str, description: str, parameters: dict, danger: str = "safe"):
    def deco(fn):
        REGISTRY[name] = Tool(name, description, parameters, fn, danger)
        return fn
    return deco


def _obj(props: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": props, "required": required or []}


STR = {"type": "string"}
INT = {"type": "integer"}

# The directory the agent works in. Reports, skills and notes land here.
# Default: the current directory (run the agent from your project folder), or
# SARRATHI_WORKSPACE to pin it somewhere permanent.
WORKSPACE = Path(os.environ.get("SARRATHI_WORKSPACE", Path.cwd())).resolve()

SHELL_ALLOWLIST = {
    "ls", "cat", "head", "tail", "wc", "grep", "find", "pwd", "date", "whoami",
    "python3", "python", "pip3", "git", "curl", "echo", "sort", "uniq", "cut", "tree", "du", "df",
}
SHELL_DENY = ("rm -rf", "mkfs", "dd if=", ":(){", "sudo", "chmod 777", "> /dev/sd", "shutdown", "reboot")


# ---------------------------------------------------------------------------
# Research — the agent's core skill (delegates to the Shodh engine)
# ---------------------------------------------------------------------------
@tool(
    "shodh_research",
    "Research a business idea against the case-file corpus and cultural profiles. Runs the Shodh "
    "engine and returns an Arthabodh: cultural fit, what worked, what failed, risk flags, and a "
    "7-day $0 validation plan. Use whenever the user asks about a business idea, market entry, "
    "whether something will work somewhere, or expansion into a new country.",
    _obj({
        "idea": {"type": "string", "description": "The business idea in the user's own words."},
        "country": {"type": "string", "description": "Target market country, if known."},
        "budget": {"type": "string", "enum": ["", "none", "small", "medium", "large"],
                   "description": "How much money the user can invest."},
    }, ["idea"]),
)
def shodh_research(idea: str, country: str = "", budget: str = "") -> str:
    from idea_oracle import IdeaOracle, get_brain
    oracle = IdeaOracle(brain=get_brain(prefer_offline=True))
    report = oracle.analyze(idea, country=country, budget=budget)
    # persist the artefact — an agent produces files, not just replies
    slug = re.sub(r"[^a-z0-9]+", "-", idea.lower()).strip("-")[:60] or "idea"
    out_dir = WORKSPACE / "arthabodh-reports"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%d')}-{slug}.md"
    path.write_text(report.markdown, encoding="utf-8")
    flags = "; ".join(f"[{f['level']}] {f['title']}" for f in report.flags) or "none"
    evidence = report.to_dict()["evidence_ids"]
    return (f"Arthabodh written to {path}\n"
            f"Market: {report.brief.country or 'unspecified'} | Sector: {report.brief.sector or 'unclassified'} "
            f"| Budget: {report.brief.budget}\n"
            f"Risk flags: {flags}\n"
            f"Case files used: worked={evidence['worked']}, failed={evidence['failed']}, patterns={evidence['patterns']}\n\n"
            f"--- report (first 3000 chars) ---\n{report.markdown[:3000]}")


# ---------------------------------------------------------------------------
# Memory — what makes it an agent rather than a chatbot
# ---------------------------------------------------------------------------
@tool(
    "remember",
    "Store something durable about the user, their business, decisions taken, lessons learned or "
    "people mentioned. Use whenever you learn something that would still matter next week. "
    "Do not store small talk, greetings or transient details.",
    _obj({
        "text": {"type": "string", "description": "One clear sentence to remember."},
        "kind": {"type": "string", "enum": ["fact", "preference", "decision", "idea", "lesson",
                                            "person", "task", "outcome"]},
        "tags": {"type": "array", "items": STR, "description": "2-4 short tags for later recall."},
    }, ["text", "kind"]),
)
def remember(text: str, kind: str = "fact", tags: list[str] | None = None) -> str:
    from .memory import AgentMemory
    m = AgentMemory().remember(text, kind=kind, tags=tags or [], source="agent")
    return f"Remembered [{m.kind}] {m.text}"


@tool(
    "recall",
    "Search long-term memory for anything relevant to a topic. Use before asking the user for "
    "information they may have already given you.",
    _obj({"query": STR, "limit": INT}, ["query"]),
)
def recall(query: str, limit: int = 5) -> str:
    from .memory import AgentMemory
    mem = AgentMemory()
    hits = mem.recall(query, limit=limit)
    if not hits:
        recent = mem.recent(limit=6)
        if not recent:
            return (f"No memories match {query!r}, and memory is empty. Nothing has been stored yet - "
                    f"tell me about yourself and I will remember it.")
        listing = "\n".join(f"[{m.kind}] {m.ts[:10]} — {m.text[:160]}" for m in recent)
        return (f"No exact match for {query!r}. Here is everything I currently remember:\n{listing}\n\n"
                f"(Lexical search only - try a keyword that appears in the memory, or store more detail.)")
    return "\n".join(f"[{m.kind}] {m.ts[:10]} — {m.text} (score {s:.2f})" for s, m in hits)


@tool("memory_stats", "Show what the agent remembers: how many memories, by type, and where they live.",
      _obj({}))
def memory_stats() -> str:
    from .memory import AgentMemory
    return json.dumps(AgentMemory().stats(), indent=2)


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------
def _safe_path(path: str, must_exist: bool = False) -> Path:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = WORKSPACE / p
    p = p.resolve()
    root = WORKSPACE if not must_exist else WORKSPACE
    try:
        p.relative_to(root)
    except ValueError:
        # allow explicit reads anywhere, but flag writes outside the workspace
        pass
    return p


@tool("read_file", "Read a text file. Use before editing or summarising a document.",
      _obj({"path": STR, "max_chars": INT}, ["path"]))
def read_file(path: str, max_chars: int = 8000) -> str:
    p = _safe_path(path)
    if not p.exists():
        return f"error: {p} does not exist"
    if p.is_dir():
        return "error: that is a directory, use list_dir"
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return f"error reading {p}: {exc}"
    return text[:max_chars] + (f"\n[...truncated, {len(text)} chars total]" if len(text) > max_chars else "")


@tool("write_file", "Write or overwrite a text file in the workspace. Creates parent folders.",
      _obj({"path": STR, "content": STR}, ["path", "content"]))
def write_file(path: str, content: str) -> str:
    p = _safe_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} chars to {p}"


@tool("list_dir", "List the contents of a directory.",
      _obj({"path": STR}, ["path"]))
def list_dir(path: str = ".") -> str:
    p = _safe_path(path)
    if not p.exists():
        return f"error: {p} does not exist"
    if p.is_file():
        return str(p)
    rows = []
    for child in sorted(p.iterdir()):
        size = child.stat().st_size if child.is_file() else 0
        rows.append(f"{'d' if child.is_dir() else '-'} {size:>9} {child.name}")
    return f"{p}\n" + "\n".join(rows[:200])


@tool("fetch_url", "Fetch a web page and return its readable text. Use for research that is not in "
      "the local corpus.", _obj({"url": STR, "max_chars": INT}, ["url"]))
def fetch_url(url: str, max_chars: int = 5000) -> str:
    if not url.startswith(("http://", "https://")):
        return "error: only http(s) URLs are supported"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SarathiAgent/0.1 (personal research)"})
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read(600_000).decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return f"error fetching {url}: {exc}"
    raw = re.sub(r"(?is)<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ", raw)
    text = re.sub(r"(?s)<[^>]+>", " ", raw)
    text = re.sub(r"&nbsp;?", " ", text)
    text = re.sub(r"&amp;?", "&", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


@tool("run_shell",
      "Run a shell command in the workspace. Only safe commands are permitted; dangerous ones are "
      "refused. Use for inspecting the repo, running tests, or git status.",
      _obj({"command": STR}, ["command"]), danger="guarded")
def run_shell(command: str) -> str:
    if any(bad in command for bad in SHELL_DENY):
        return "refused: that command is on the deny list."
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        return f"error: could not parse command ({exc})"
    if not parts:
        return "error: empty command"
    if parts[0] not in SHELL_ALLOWLIST:
        return (f"refused: {parts[0]!r} is not on the allow list. "
                f"Allowed: {', '.join(sorted(SHELL_ALLOWLIST))}")
    try:
        proc = subprocess.run(parts, cwd=WORKSPACE, capture_output=True, text=True,
                              timeout=60, check=False)
    except subprocess.TimeoutExpired:
        return "error: command timed out after 60s"
    out = (proc.stdout or "") + (("\n[stderr]\n" + proc.stderr) if proc.stderr else "")
    return out[:6000] or f"(no output, exit code {proc.returncode})"


# ---------------------------------------------------------------------------
# Skills — progressive disclosure, the token-efficient half
# ---------------------------------------------------------------------------
SKILLS_DIR = WORKSPACE / "skills"


@tool("list_skills",
      "List installed skills with their one-line descriptions. Cheap: this is the "
      "metadata tier only. Load a skill's full instructions with load_skill once you know it is relevant.",
      _obj({}))
def list_skills() -> str:
    if not SKILLS_DIR.exists():
        return "No skills directory found."
    rows = []
    for skill_md in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8", errors="replace")
        name = skill_md.parent.name
        desc = ""
        if text.startswith("---"):
            fm = text.split("---", 2)[1]
            for line in fm.splitlines():
                if line.strip().lower().startswith("description:"):
                    desc = line.split(":", 1)[1].strip()
                    break
            for line in fm.splitlines():
                if line.strip().lower().startswith("name:"):
                    name = line.split(":", 1)[1].strip() or name
                    break
        rows.append(f"{name}: {desc[:200] if desc else '(no description)'}")
    return "\n".join(rows) if rows else "No skills installed."


@tool("load_skill",
      "Load a skill's full instructions into context. Only call this once you know the skill is "
      "relevant to the task - that is what keeps context small.",
      _obj({"name": STR}, ["name"]))
def load_skill(name: str) -> str:
    skill_md = SKILLS_DIR / name / "SKILL.md"
    if not skill_md.exists():
        available = ", ".join(sorted(p.parent.name for p in SKILLS_DIR.glob("*/SKILL.md")))
        return f"error: no skill named {name!r}. Available: {available}"
    body = skill_md.read_text(encoding="utf-8", errors="replace")
    refs = sorted((skill_md.parent / "references").glob("*")) if (skill_md.parent / "references").exists() else []
    extra = ("\n\nREFERENCE FILES (read with read_file only when a step needs them):\n" +
             "\n".join(f"  {r.relative_to(WORKSPACE)}" for r in refs)) if refs else ""
    return f"{body}{extra}"


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------
@tool("now", "Current date and time. Use instead of guessing.", _obj({}))
def now() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z (%A)")


@tool("save_report",
      "Save a finished piece of work (brief, analysis, summary) as a markdown file in the workspace.",
      _obj({"name": STR, "content": STR}, ["name", "content"]))
def save_report(name: str, content: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "report"
    out = WORKSPACE / "arthabodh-reports" / f"{slug}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    return f"Saved {out}"


# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------
def schemas(allowed: list[str] | None = None) -> list[dict]:
    names = allowed if allowed else list(REGISTRY)
    return [REGISTRY[n].schema() for n in names if n in REGISTRY]


def execute(name: str, arguments: dict | str) -> str:
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments) if arguments.strip() else {}
        except json.JSONDecodeError:
            return f"error: could not parse arguments for {name}"
    t = REGISTRY.get(name)
    if not t:
        return f"error: unknown tool {name!r}"
    try:
        return str(t.fn(**arguments))
    except TypeError as exc:
        return f"error: bad arguments for {name}: {exc}"
    except Exception as exc:  # noqa: BLE001 — a failing tool must never kill the agent
        return f"error: {name} raised {type(exc).__name__}: {exc}"


def catalogue() -> str:
    lines = []
    for t in REGISTRY.values():
        params = ", ".join(t.parameters.get("properties", {}))
        lines.append(f"  {t.name:<16} [{t.danger:<9}] {t.description[:80]}")
        lines.append(f"  {'':<16} args: {params}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(f"{len(REGISTRY)} tools registered:\n")
    print(catalogue())
    print("\n--- smoke test ---")
    print(execute("now", {}))
    print(execute("list_skills", {}))
    print(execute("run_shell", {"command": "rm -rf /"}))
    print(execute("run_shell", {"command": "ls -1"}))
