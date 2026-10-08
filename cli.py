#!/usr/bin/env python3
"""
cli.py — run Arthabodh from the terminal. Zero dependencies, zero cost.

    Arthabodh  the product report you receive
    Shodh      the engine that researches it   (Sarathi Labs)

Examples
--------
    python cli.py --idea "I want to open a specialty coffee chain in Melbourne" --country Australia
    python cli.py --idea "mobile money app for farmers" --country Kenya --out report.md
    python cli.py --providers            # show which free brains are available
    python cli.py --demo                 # run a built-in example
    python cli.py                        # interactive mode
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from idea_oracle import IdeaOracle, describe_providers, get_brain  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Arthabodh by Sarathi Labs — research any business idea against culture + case files.",
        epilog="Shodh your idea. Get your Arthabodh.")
    ap.add_argument("--idea", help="Your business idea in plain English.")
    ap.add_argument("--country", default="", help="Target market country (optional; auto-detected from the idea).")
    ap.add_argument("--budget", default="", choices=["", "none", "small", "medium", "large"],
                    help="How much you can invest. Default: auto-detect.")
    ap.add_argument("--out", help="Write the markdown report to this file.")
    ap.add_argument("--offline", action="store_true", help="Force rule-based mode (no LLM, no API calls).")
    ap.add_argument("--providers", action="store_true", help="Show the free brains and their status.")
    ap.add_argument("--demo", action="store_true", help="Run a built-in example idea.")
    ap.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    args = ap.parse_args()

    if args.providers:
        print(describe_providers())
        return 0

    if args.demo:
        args.idea = ("Existing family bakery in Naples, Italy. We want to export packaged biscuits "
                     "to supermarkets in Germany and the UK. Small budget, no marketing team.")

    if not args.idea:
        print("Arthabodh (Sarathi Labs) — describe your idea. Blank line to finish.\n")
        lines: list[str] = []
        while True:
            try:
                line = input("> ")
            except (EOFError, KeyboardInterrupt):
                break
            if not line.strip():
                break
            lines.append(line)
        args.idea = " ".join(lines).strip()
        if not args.idea:
            print("No idea given. Try --demo.")
            return 1

    brain = get_brain(prefer_offline=args.offline)
    oracle = IdeaOracle(brain=brain)
    print(f"\n[shodh] engine ready · [brain] {brain.label}\n", file=sys.stderr)
    report = oracle.analyze(args.idea, country=args.country, budget=args.budget)

    output = __import__("json").dumps(report.to_dict(), indent=2) if args.json else report.markdown
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"Your Arthabodh was written to {args.out}", file=sys.stderr)
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
