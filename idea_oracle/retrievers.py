"""
retrievers.py — dependency-free retrieval over the knowledge base.

Why hand-rolled TF-IDF instead of a vector database?
  * the dataset here is tiny (dozens to a few thousand docs)
  * classic lexical retrieval is *better* than embeddings on short entity-heavy
    queries ("Jollibee", "M-Pesa", "cash on delivery") because exact terms and
    citations matter more than fuzzy semantic similarity
  * it runs on any machine with zero installs and zero API calls

When your corpus grows past ~5,000 documents, swap in the vector path:
  pip install chromadb sentence-transformers   # both free, both run locally
  see docs/ROADMAP.md step 5 for the drop-in upgrade.
"""

from __future__ import annotations

import csv
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "than", "of", "to", "in", "on",
    "for", "with", "is", "are", "was", "were", "be", "been", "being", "it", "its", "this",
    "that", "these", "those", "as", "at", "by", "from", "into", "about", "i", "we", "you",
    "my", "our", "your", "they", "them", "their", "he", "she", "his", "her", "do", "does",
    "did", "will", "would", "can", "could", "should", "have", "has", "had", "not", "no",
    "so", "up", "out", "how", "what", "when", "where", "which", "who", "want", "like",
}


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9][a-z0-9\-']+", text.lower()) if t not in STOPWORDS and len(t) > 2]


def stem(token: str) -> str:
    """Very light suffix stripping - good enough for matching plurals/gerunds."""
    for suffix in ("ies", "ing", "ers", "er", "ed", "es", "s"):
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


@dataclass
class Document:
    id: str
    text: str
    payload: dict
    kind: str = "generic"
    tokens: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.tokens = [stem(t) for t in tokenize(self.text)]


class TfidfIndex:
    """Classic TF-IDF with cosine similarity. ~50 lines, no dependencies."""

    def __init__(self, documents: list[Document]):
        self.docs = documents
        self.df: dict[str, int] = {}
        for d in documents:
            for term in set(d.tokens):
                self.df[term] = self.df.get(term, 0) + 1
        self.n = max(len(documents), 1)
        self.vectors = [self._vectorise(d.tokens) for d in documents]
        self.norms = [self._norm(v) for v in self.vectors]

    def _idf(self, term: str) -> float:
        return math.log((self.n + 1) / (self.df.get(term, 0) + 1)) + 1.0

    def _vectorise(self, tokens: list[str]) -> dict[str, float]:
        counts: dict[str, float] = {}
        for t in tokens:
            counts[t] = counts.get(t, 0.0) + 1.0
        length = max(len(tokens), 1)
        return {t: (c / length) * self._idf(t) for t, c in counts.items()}

    @staticmethod
    def _norm(vec: dict[str, float]) -> float:
        return math.sqrt(sum(v * v for v in vec.values())) or 1.0

    def search(self, query: str, top_k: int = 5, kind: str | None = None) -> list[tuple[float, Document]]:
        q_tokens = [stem(t) for t in tokenize(query)]
        if not q_tokens:
            return []
        q_vec = self._vectorise(q_tokens)
        q_norm = self._norm(q_vec)
        scored: list[tuple[float, Document]] = []
        for idx, d in enumerate(self.docs):
            if kind and d.kind != kind:
                continue
            dot = 0.0
            for term, weight in q_vec.items():
                dv = self.vectors[idx].get(term)
                if dv:
                    dot += weight * dv
            if dot:
                scored.append((dot / (q_norm * self.norms[idx]), d))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]


# ---------------------------------------------------------------------------
# Knowledge base loader
# ---------------------------------------------------------------------------
class KnowledgeBase:
    def __init__(self, data_dir: Path | str = DATA_DIR):
        self.data_dir = Path(data_dir)
        self.cultures: dict[str, dict] = {}
        self.cases: list[dict] = []
        self.patterns: list[dict] = []
        self._load()
        self.index = TfidfIndex(self._build_documents())

    # -- loading -----------------------------------------------------------
    def _load(self) -> None:
        with open(self.data_dir / "cultures.csv", newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                self.cultures[row["country"].strip().lower()] = row

        with open(self.data_dir / "case_studies.json", encoding="utf-8") as fh:
            self.cases = json.load(fh)["cases"]

        with open(self.data_dir / "patterns.json", encoding="utf-8") as fh:
            self.patterns = json.load(fh)["patterns"]

    def _build_documents(self) -> list[Document]:
        docs: list[Document] = []
        for c in self.cases:
            text = " ".join(
                str(c.get(k, ""))
                for k in ("name", "sector", "model", "region", "country", "outcome",
                          "what_worked", "what_didnt", "key_lesson")
            ) + " " + " ".join(c.get("tags", [])) + " " + " ".join(c.get("cultural_factors", []))
            docs.append(Document(id=c["id"], text=text, payload=c, kind="case"))

        for p in self.patterns:
            text = " ".join(
                [p["name"], p["essence"], p.get("resource_level", "")]
                + p.get("worked_where", [])
                + p.get("failed_where", [])
                + p.get("signals_you_need_it", [])
            )
            docs.append(Document(id=p["id"], text=text, payload=p, kind="pattern"))

        for name, c in self.cultures.items():
            text = f"{c['country']} {c['region']} {c['business_notes']} culture market entry"
            docs.append(Document(id=name, text=text, payload=c, kind="culture"))
        return docs

    # -- queries -----------------------------------------------------------
    def culture_profile(self, country: str) -> dict | None:
        if not country:
            return None
        key = country.strip().lower()
        if key in self.cultures:
            return self.cultures[key]
        for name, row in self.cultures.items():
            if key in name or name in key:
                return row
        return None

    @staticmethod
    def _boost(query_terms: set[str], doc: Document) -> float:
        """Small lexical boost so exact tag/sector/name hits outrank vague prose matches."""
        p = doc.payload
        meta = " ".join(str(x) for x in (
            p.get("tags", []), p.get("sector", ""), p.get("name", ""), p.get("country", ""), p.get("region", "")
        ))
        overlap = len(query_terms & {stem(t) for t in tokenize(meta)})
        return 0.18 * min(overlap, 3)

    def find_cases(self, query: str, top_k: int = 5, outcome: str | None = None,
                   prefer_country: str = "", prefer_region: str = "") -> list[dict]:
        results = self.index.search(query, top_k=top_k * 6, kind="case")
        q_terms = {stem(t) for t in tokenize(query)}

        # If the user names a market we hold cases for, those cases must always be
        # considered - lexical overlap alone would silently drop them for vague queries.
        seen_ids = {doc.id for _, doc in results}
        if prefer_country or prefer_region:
            for doc in self.index.docs:
                if doc.kind != "case" or doc.id in seen_ids:
                    continue
                c = doc.payload
                local = (prefer_country and prefer_country.lower() in str(c.get("country", "")).lower()) or \
                        (prefer_region and prefer_region.lower() == str(c.get("region", "")).lower())
                if local:
                    results.append((self._boost(q_terms, doc), doc))
                    seen_ids.add(doc.id)

        def affinity(doc: Document) -> float:
            """Regional cases are more decision-relevant than culturally distant ones."""
            c = doc.payload
            bonus = 0.0
            if prefer_country and prefer_country.lower() in str(c.get("country", "")).lower():
                bonus += 0.35
            if prefer_region and prefer_region.lower() == str(c.get("region", "")).lower():
                bonus += 0.15
            return bonus

        scored = [(score + self._boost(q_terms, doc) + affinity(doc), doc) for score, doc in results]
        scored.sort(key=lambda x: x[0], reverse=True)
        out, seen = [], set()
        for score, doc in scored:
            if score <= 0.02:
                continue
            c = doc.payload
            if outcome and c.get("outcome") != outcome:
                continue
            if c["id"] in seen:
                continue
            seen.add(c["id"])
            out.append(c)
            if len(out) >= top_k:
                break
        return out

    def find_patterns(self, query: str, top_k: int = 4) -> list[dict]:
        results = self.index.search(query, top_k=top_k * 3, kind="pattern")
        q_terms = {stem(t) for t in tokenize(query)}
        scored = [(score + self._boost(q_terms, doc), doc) for score, doc in results]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc.payload for score, doc in scored if score > 0.02][:top_k]

    def all_countries(self) -> list[str]:
        return sorted(row["country"] for row in self.cultures.values())


if __name__ == "__main__":
    kb = KnowledgeBase()
    print(f"Loaded {len(kb.cases)} case files, {len(kb.patterns)} patterns, {len(kb.cultures)} cultures.\n")
    for q in ["cash on delivery grocery delivery", "coffee chain local competition", "escape room entertainment"]:
        print(f"QUERY: {q}")
        for c in kb.find_cases(q, top_k=3):
            print(f"   - [{c['outcome']:<6}] {c['name']} ({c['region']})")
        for p in kb.find_patterns(q, top_k=2):
            print(f"   * pattern: {p['name']}")
        print()
