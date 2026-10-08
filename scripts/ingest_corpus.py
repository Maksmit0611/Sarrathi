#!/usr/bin/env python3
"""
ingest_corpus.py — build a retrievable corpus from your OWN documents.

Turns a folder of .txt / .md / .csv files into chunked JSONL that the agent can
retrieve from. Zero dependencies. This is the "RAG without a vector DB" path:
lexical retrieval over well-chunked text beats vector search over badly-chunked
text, and it costs nothing to run.

Usage
-----
    python scripts/ingest_corpus.py --input ~/my-research --out data/my_corpus.jsonl
    python scripts/ingest_corpus.py --input notes.md --out data/my_corpus.jsonl --chunk-words 250

Then point the agent at it:
    from idea_oracle.retrievers import KnowledgeBase
    # see docs/ROADMAP.md step 5 for wiring an extra corpus kind
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

SUPPORTED = {".txt", ".md", ".markdown", ".csv", ".tsv"}


def read_file(path: Path) -> str:
    if path.suffix.lower() in {".csv", ".tsv"}:
        delim = "\t" if path.suffix.lower() == ".tsv" else ","
        with open(path, newline="", encoding="utf-8", errors="replace") as fh:
            rows = list(csv.DictReader(fh, delimiter=delim))
        return "\n".join(
            " | ".join(f"{k}: {v}" for k, v in row.items() if v and v.strip()) for row in rows[:5000]
        )
    return path.read_text(encoding="utf-8", errors="replace")


def chunk(text: str, target_words: int, overlap_words: int) -> list[str]:
    """Paragraph-aware chunking: never split mid-sentence if a paragraph fits."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf: list[str] = []
    count = 0
    for para in paragraphs:
        w = len(para.split())
        if count + w > target_words and buf:
            chunks.append("\n\n".join(buf))
            tail = " ".join(" ".join(buf).split()[-overlap_words:]) if overlap_words else ""
            buf, count = ([tail] if tail else []), (len(tail.split()) if tail else 0)
        buf.append(para)
        count += w
    if buf:
        chunks.append("\n\n".join(buf))
    # guard against a single monster paragraph
    final: list[str] = []
    for c in chunks:
        words = c.split()
        if len(words) <= target_words * 2:
            final.append(c)
        else:
            for i in range(0, len(words), target_words - overlap_words):
                final.append(" ".join(words[i : i + target_words]))
    return [c for c in final if len(c.split()) > 15]


def main() -> int:
    ap = argparse.ArgumentParser(description="Ingest documents into a retrievable corpus.")
    ap.add_argument("--input", required=True, help="File or folder to ingest.")
    ap.add_argument("--out", default="data/my_corpus.jsonl", help="Output JSONL path.")
    ap.add_argument("--chunk-words", type=int, default=300)
    ap.add_argument("--overlap-words", type=int, default=40)
    args = ap.parse_args()

    src = Path(args.input).expanduser()
    files = [src] if src.is_file() else [p for p in sorted(src.rglob("*")) if p.suffix.lower() in SUPPORTED]
    if not files:
        print(f"No supported files found in {src} (looking for: {', '.join(sorted(SUPPORTED))})")
        return 1

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    with open(out_path, "w", encoding="utf-8") as out:
        for path in files:
            text = read_file(path)
            pieces = chunk(text, args.chunk_words, args.overlap_words)
            for i, piece in enumerate(pieces):
                doc_id = hashlib.sha1(f"{path}:{i}".encode()).hexdigest()[:12]
                out.write(json.dumps({
                    "id": doc_id,
                    "kind": "custom",
                    "source": str(path),
                    "chunk": i,
                    "text": piece,
                }, ensure_ascii=False) + "\n")
            total += len(pieces)
            print(f"  {len(pieces):>4} chunks  {path}")

    print(f"\nWrote {total} chunks from {len(files)} file(s) -> {out_path}")
    print("Next: wire this file into retrievers.KnowledgeBase (see docs/ROADMAP.md step 5).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
