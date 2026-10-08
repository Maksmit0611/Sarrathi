"""
memory.py — persistent memory for the Sarathi agent.

An app forgets you between visits. An agent doesn't. This module is what makes
that difference real.

Three tiers, cheapest first (the standard agent-memory ladder):

    Tier 1  session buffer      the current conversation          (in RAM)
    Tier 2  facts store         durable statements, append-only   (~/.sarrathi/memory/facts.jsonl)
    Tier 3  recall              TF-IDF search over those facts    (reuses idea_oracle.retrievers)

Why JSONL and not a vector database: it is append-only (never corrupts), it is
human-readable and greppable, it diffs in git, and at a few thousand facts plain
lexical search beats embeddings. Swap in Chroma past ~5,000 facts — the
`recall()` signature stays the same.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from idea_oracle.retrievers import Document, TfidfIndex  # reuse the engine's index

MEMORY_KINDS = ("fact", "preference", "decision", "idea", "lesson", "person", "task", "outcome")

# Asking "what do you know about my budget?" should match a memory phrased
# "I refuse to spend money". TF-IDF has no synonyms, so we strip the question
# scaffolding instead — it is free, offline, and gets the common cases.
STOPWORDS = {
    "what", "do", "you", "know", "about", "my", "me", "i", "the", "a", "an", "is", "are", "was",
    "tell", "again", "remind", "did", "we", "us", "our", "have", "has", "had", "to", "of", "in",
    "on", "for", "and", "or", "it", "that", "this", "there", "any", "anything", "something",
    "please", "can", "could", "would", "should", "say", "said", "got", "get", "remember",
    "memory", "recall", "search", "anything", "everything", "still", "back", "from", "with",
}


def clean_query(query: str) -> str:
    words = [w for w in re.findall(r"[A-Za-z0-9']+", query.lower())]
    kept = [w for w in words if w not in STOPWORDS and len(w) > 2]
    return " ".join(kept) or query


_HOME_OVERRIDE: Path | None = None


def set_home(path: Path | str) -> Path:
    """
    Point every part of the agent (loop, tools, identity) at one agent home.
    Without this, a tool call could write memory in a different place from the
    session that made it - which is exactly the kind of bug that makes an agent
    look forgetful.
    """
    global _HOME_OVERRIDE
    _HOME_OVERRIDE = Path(path).expanduser()
    os.environ["SARRATHI_HOME"] = str(_HOME_OVERRIDE)
    return _HOME_OVERRIDE


def default_home() -> Path:
    if _HOME_OVERRIDE is not None:
        return _HOME_OVERRIDE
    return Path(os.environ.get("SARRATHI_HOME", Path.home() / ".sarrathi"))


@dataclass
class Memory:
    ts: str
    kind: str
    text: str
    tags: list[str] = field(default_factory=list)
    source: str = "agent"
    confidence: str = "medium"

    def line(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


class AgentMemory:
    """Durable, searchable, human-readable memory."""

    def __init__(self, home: Path | str | None = None):
        self.home = Path(home) if home else default_home()
        self.mem_dir = self.home / "memory"
        self.sessions_dir = self.mem_dir / "sessions"
        self.facts_path = self.mem_dir / "facts.jsonl"
        self.identity_dir = self.home / "identity"
        self.reports_dir = self.home / "reports"
        self.logs_dir = self.home / "logs"
        for d in (self.mem_dir, self.sessions_dir, self.identity_dir, self.reports_dir, self.logs_dir):
            d.mkdir(parents=True, exist_ok=True)
        self._index: TfidfIndex | None = None
        self._loaded: list[Memory] = []

    # -- writing -----------------------------------------------------------
    def remember(self, text: str, kind: str = "fact", tags: list[str] | None = None,
                 source: str = "agent", confidence: str = "medium") -> Memory:
        if kind not in MEMORY_KINDS:
            kind = "fact"
        text = " ".join(text.split()).strip()
        if not text:
            raise ValueError("refusing to store an empty memory")
        # de-duplicate: identical text (case-insensitive) is not stored twice
        for existing in self.load():
            if existing.text.lower() == text.lower():
                return existing
        m = Memory(ts=datetime.now(timezone.utc).isoformat(timespec="seconds"), kind=kind,
                   text=text, tags=tags or [], source=source, confidence=confidence)
        with open(self.facts_path, "a", encoding="utf-8") as fh:
            fh.write(m.line() + "\n")
        self._index = None
        self._loaded.append(m)
        self._write_digest()
        return m

    def log_turn(self, role: str, content: str) -> None:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        rec = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "role": role,
               "content": content[:4000]}
        with open(self.sessions_dir / f"{day}.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # -- reading -----------------------------------------------------------
    def load(self) -> list[Memory]:
        if self._loaded:
            return self._loaded
        if not self.facts_path.exists():
            return []
        out: list[Memory] = []
        with open(self.facts_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    out.append(Memory(ts=d.get("ts", ""), kind=d.get("kind", "fact"),
                                      text=d.get("text", ""), tags=d.get("tags", []),
                                      source=d.get("source", "agent"),
                                      confidence=d.get("confidence", "medium")))
                except json.JSONDecodeError:
                    continue  # never let one bad line kill memory
        self._loaded = out
        return out

    def recall(self, query: str, limit: int = 5, kind: str | None = None) -> list[tuple[float, Memory]]:
        """Search memory. Lexical, cited, offline - same engine as the research corpus."""
        facts = [m for m in self.load() if not kind or m.kind == kind]
        if not facts or not query.strip():
            return []
        query = clean_query(query)
        if self._index is None:
            self._index = TfidfIndex([
                Document(id=str(i), text=f"{m.text} {' '.join(m.tags)} {m.kind}", payload={})
                for i, m in enumerate(facts)
            ])
        hits = self._index.search(query, top_k=limit)
        return [(score, facts[int(doc.id)]) for score, doc in hits if score > 0.02]

    def recent(self, limit: int = 10, kind: str | None = None) -> list[Memory]:
        facts = [m for m in self.load() if not kind or m.kind == kind]
        return facts[-limit:][::-1]

    def stats(self) -> dict:
        facts = self.load()
        by_kind: dict[str, int] = {}
        for m in facts:
            by_kind[m.kind] = by_kind.get(m.kind, 0) + 1
        sessions = sorted(self.sessions_dir.glob("*.jsonl"))
        return {
            "facts": len(facts),
            "by_kind": by_kind,
            "sessions": len(sessions),
            "oldest": facts[0].ts[:10] if facts else None,
            "newest": facts[-1].ts[:10] if facts else None,
            "home": str(self.home),
        }

    # -- digest ------------------------------------------------------------
    def _write_digest(self) -> None:
        """A human-readable MEMORY.md - so you can read your agent's mind, and edit it."""
        facts = self.load()
        by_kind: dict[str, list[Memory]] = {}
        for m in facts:
            by_kind.setdefault(m.kind, []).append(m)

        lines = ["# Sarathi — memory digest", "",
                 f"*Auto-generated from `facts.jsonl`. Last updated "
                 f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · {len(facts)} memories.*", "",
                 "> Edit this file to fix a wrong memory, but the source of truth is `facts.jsonl`.", ""]
        titles = {"preference": "What I know about you", "fact": "Facts",
                  "decision": "Decisions taken", "idea": "Ideas you're exploring",
                  "lesson": "Lessons learned", "person": "People", "task": "Open threads",
                  "outcome": "Outcomes"}
        order = ["preference", "person", "decision", "idea", "task", "outcome", "lesson", "fact"]
        for kind in order:
            items = by_kind.get(kind)
            if not items:
                continue
            lines.append(f"## {titles.get(kind, kind.title())}")
            for m in items[-40:]:
                date = m.ts[:10]
                tag = f" `{' '.join(m.tags)}`" if m.tags else ""
                lines.append(f"- **{date}** — {m.text}{tag}")
            lines.append("")
        (self.mem_dir / "MEMORY.md").write_text("\n".join(lines), encoding="utf-8")

    # -- context for the model --------------------------------------------
    def context_block(self, query: str = "", max_chars: int = 2500) -> str:
        """What the agent carries into a turn: recent facts + anything relevant to this query."""
        parts: list[str] = []
        recent = self.recent(limit=12)
        if recent:
            parts.append("RECENT MEMORY (most recent first):")
            for m in recent:
                parts.append(f"  [{m.kind}] {m.ts[:10]} — {m.text[:220]}")
        if query:
            hits = self.recall(query, limit=5)
            if hits:
                parts.append("\nRELEVANT TO THIS REQUEST:")
                for score, m in hits:
                    parts.append(f"  [{m.kind}] {m.ts[:10]} — {m.text[:220]}")
        block = "\n".join(parts)
        if len(block) > max_chars:
            block = block[:max_chars] + "\n  [memory truncated]"
        return block


if __name__ == "__main__":
    mem = AgentMemory(home="/tmp/sarrathi-mem-demo")
    mem.remember("Prefers to be called Max. Located in Melbourne, Australia.", "preference",
                 ["name", "location"])
    mem.remember("Is building a business-idea research agent called Arthabodh.", "fact", ["project"])
    mem.remember("Decided not to invest money in the project - zero budget constraint.", "decision",
                 ["budget", "constraint"])
    print("stats:", json.dumps(mem.stats(), indent=2))
    print("\nrecall 'budget':")
    for score, m in mem.recall("budget"):
        print(f"  {score:.3f}  [{m.kind}] {m.text}")
    print("\ncontext block:\n" + mem.context_block("what should I know about money"))
