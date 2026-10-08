#!/usr/bin/env python3
"""
fetch_data.py — download or point you at the free public datasets that expand
the Arthabodh (Sarathi Labs) knowledge base.

Nothing here requires a key or a payment. Kaggle datasets need a free account
(and optionally the `kaggle` CLI with a free API token), so those are printed as
instructions rather than downloaded automatically — respect each licence.

Usage
-----
    python scripts/fetch_data.py --list          # show every source with licence + link
    python scripts/fetch_data.py --get hofstede  # attempt a direct download where one exists
    python scripts/fetch_data.py --check         # verify what is already in data/
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

SOURCES = {
    "hofstede": {
        "name": "Hofstede dimension data matrix (6 dimensions, ~100 countries)",
        "url": "https://geerthofstede.com/research-and-vsm/dimension-data-matrix/",
        "licence": "Free for research use; commercial use requires permission from the authors.",
        "direct": False,
        "note": "Download the CSV/XLS from the page, then replace data/cultures.csv. "
                "Set 'region' and 'business_notes' columns yourself.",
    },
    "wvs": {
        "name": "World Values Survey (raw longitudinal microdata)",
        "url": "https://www.worldvaluessurvey.org/WVSContents.jsp",
        "licence": "Openly available to researchers; check per-wave terms.",
        "direct": False,
        "note": "Free registration. Use R or Python (pandas) to compute your own indices.",
    },
    "worldbank": {
        "name": "World Bank Open Data API (business conditions, connectivity, finance)",
        "url": "https://api.worldbank.org/v2/country/AUS/indicator/IC.BUS.NREG?format=json",
        "licence": "CC BY 4.0",
        "direct": True,
        "note": "Public JSON API, no key. Swap the indicator code for any of thousands of series.",
    },
    "kaggle_startup_failures": {
        "name": "Kaggle — Startup Failures (814 companies, 13 failure-cause flags)",
        "url": "https://www.kaggle.com/datasets/dagloxkankwanda/startup-failures",
        "licence": "CC BY-NC 4.0 (non-commercial). Do not ship commercially without licensing.",
        "direct": False,
        "note": "Free Kaggle account. Best single source of labelled failure causes.",
    },
    "kaggle_crunchbase": {
        "name": "Kaggle — Startup Success/Fail from Crunchbase",
        "url": "https://www.kaggle.com/datasets/yanmaksi/big-startup-secsees-fail-dataset-from-crunchbase",
        "licence": "Check dataset page.",
        "direct": False,
        "note": "Good for training a success/failure classifier as a second opinion model.",
    },
    "kaggle_financial_distress": {
        "name": "Kaggle — Financial Distress (Altman/Ohlson-derived)",
        "url": "https://www.kaggle.com/datasets/shebrahimi/financial-distress",
        "licence": "Check dataset page.",
        "direct": False,
        "note": "Quantitative failure features; useful if you add a numeric risk score.",
    },
    "cbinsights": {
        "name": "CB Insights — Startup failure post-mortem index (public)",
        "url": "https://www.cbinsights.com/research/startup-failure-post-mortem/",
        "licence": "Free to read and cite; do not bulk-copy their text into your corpus.",
        "direct": False,
        "note": "Use it to find which companies to write your own case files about.",
    },
    "edgar": {
        "name": "SEC EDGAR full-text search (primary filings)",
        "url": "https://efts.sec.gov/LATEST/search-index?q=%22risk+factors%22",
        "licence": "Public domain (US government). Fair-access rate limits apply.",
        "direct": False,
        "note": "The primary source for any US outcome claim. Free API, be polite with rate limits.",
    },
    "awesome_free_llm": {
        "name": "awesome-freellm-apis — 134+ free LLM APIs from 40+ providers",
        "url": "https://github.com/open-free-llm-api/awesome-freellm-apis",
        "licence": "See repo.",
        "direct": False,
        "note": "Bookmark this. Free model rosters rotate monthly; this tracks them.",
    },
}


def listing() -> None:
    print(f"{len(SOURCES)} free data sources\n" + "=" * 72)
    for key, s in SOURCES.items():
        print(f"\n[{key}] {s['name']}")
        print(f"  url     : {s['url']}")
        print(f"  licence : {s['licence']}")
        print(f"  note    : {s['note']}")


def check() -> None:
    print("Current data/ contents:")
    if not DATA.exists():
        print("  (no data/ directory)")
        return
    for p in sorted(DATA.iterdir()):
        print(f"  {p.stat().st_size:>9,} bytes  {p.name}")
    try:
        cases = json.loads((DATA / "case_studies.json").read_text())["cases"]
        from collections import Counter
        print("\nCorpus health:")
        print("  cases      :", len(cases))
        print("  outcomes   :", dict(Counter(c.get("outcome") for c in cases)))
        print("  confidence :", dict(Counter(c.get("confidence") for c in cases)))
        print("  regions    :", dict(Counter(c.get("region") for c in cases)))
        fails = sum(1 for c in cases if c.get("outcome") == "failed")
        works = sum(1 for c in cases if c.get("outcome") == "worked")
        if works and fails / max(works, 1) < 0.5:
            print(f"  ⚠️  only {fails} failure records per {works} successes — add more failures.")
    except Exception as exc:  # noqa: BLE001
        print("  (could not analyse corpus:", exc, ")")


def get(key: str) -> None:
    s = SOURCES.get(key)
    if not s:
        print(f"Unknown source '{key}'. Run --list.")
        return
    if not s["direct"]:
        print(f"'{key}' needs a manual download.\n\n  {s['url']}\n\n  licence: {s['licence']}\n  {s['note']}")
        return
    print(f"Fetching {s['name']} ...")
    try:
        req = urllib.request.Request(s["url"], headers={"User-Agent": "arthabodh-sarathi-labs/0.2"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read()
        out = DATA / "worldbank_sample.json"
        DATA.mkdir(exist_ok=True)
        out.write_bytes(body)
        print(f"Saved {len(body):,} bytes -> {out}")
    except Exception as exc:  # noqa: BLE001
        print("Download failed:", exc)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--get", metavar="KEY")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.list:
        listing()
    elif args.get:
        get(args.get)
    elif args.check:
        check()
    else:
        ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
