"""
Regression tests for Arthabodh (Sarathi Labs). Runs on the standard library alone:

    python tests/test_intake.py        # or: pytest tests/

These lock in the behaviours that broke during development, so they stay fixed.
Everything here is deterministic and offline — no API keys, no network.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from idea_oracle import IdeaOracle, KnowledgeBase, OfflineBrain, parse_idea  # noqa: E402

PASS = 0
FAIL = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {label}")
    else:
        FAIL += 1
        print(f"  ✗ {label} {detail}")


# ---------------------------------------------------------------------------
# 1. Intake: country detection (regression: "Australian wine" once matched "Australia";
#    "export to Germany and the UK" once returned the wrong market)
# ---------------------------------------------------------------------------
COUNTRY_CASES = [
    ("Existing family bakery in Naples, Italy. We want to export packaged biscuits to supermarkets in Germany and the UK.", "Germany"),
    ("I want to expand from Australia into Japan with a coffee brand", "Japan"),
    ("mobile savings app for smallholder farmers in Kenya, no budget", "Kenya"),
    ("I live in India and want to open a restaurant in Dubai", "United Arab Emirates"),
    ("laundry pickup service in Mumbai, India", "India"),
    ("VR arcade in Riyadh, Saudi Arabia for teenagers", "Saudi Arabia"),
    ("I want to sell Australian wine to customers in Singapore", "Singapore"),
    ("specialty coffee subscription in Melbourne, Australia delivered by bike", "Australia"),
    ("grocery delivery app for Jakarta, Indonesia, cash on delivery", "Indonesia"),
    ("a SaaS tool for UK landlords", "United Kingdom"),
]


def test_intake() -> None:
    print("\nIntake — country detection")
    kb = KnowledgeBase()
    for text, expected in COUNTRY_CASES:
        got = parse_idea(text, kb).country
        check(f"'{text[:46]}...' -> {expected}", got == expected, f"(got {got!r})")

    print("\nIntake — sector, budget and stage")
    b = parse_idea("I already run a bakery in Italy, want to export biscuits, small budget", kb)
    check("stage detected as existing_business", b.stage == "existing_business", f"(got {b.stage!r})")
    check("sector detected as food", b.sector == "food", f"(got {b.sector!r})")
    check("budget detected as small", b.budget == "small", f"(got {b.budget!r})")

    b2 = parse_idea("I have no money at all and want to start a cleaning service in Sydney", kb)
    check("zero budget detected", b2.budget == "none", f"(got {b2.budget!r})")
    for phrase in ("no budget", "zero budget", "no funding", "cannot afford it"):
        b3 = parse_idea(f"a tiffin service in Bengaluru, {phrase}", kb)
        check(f"zero-capital phrase recognised: '{phrase}'", b3.budget == "none", f"(got {b3.budget!r})")
    check("origin marker not mistaken for target", b2.country == "Australia", f"(got {b2.country!r})")


# ---------------------------------------------------------------------------
# 2. Corpus integrity
# ---------------------------------------------------------------------------
def test_corpus() -> None:
    print("\nCorpus integrity")
    kb = KnowledgeBase()
    check("corpus has at least 30 case files", len(kb.cases) >= 30, f"({len(kb.cases)})")
    check("corpus has at least 10 patterns", len(kb.patterns) >= 10, f"({len(kb.patterns)})")
    check("corpus covers at least 15 markets", len(kb.cultures) >= 15, f"({len(kb.cultures)})")

    ids = [c["id"] for c in kb.cases]
    check("case ids are unique", len(ids) == len(set(ids)))

    required = ("id", "outcome", "what_worked", "what_didnt", "cultural_factors",
                "key_lesson", "confidence", "source_type")
    incomplete = [c.get("id") for c in kb.cases if not all(k in c for k in required)]
    check("every record has all required fields", not incomplete, f"(missing: {incomplete})")

    outcomes = {c["outcome"] for c in kb.cases}
    check("every outcome value is valid", outcomes <= {"worked", "failed", "mixed"}, f"({outcomes})")

    fails = sum(1 for c in kb.cases if c["outcome"] == "failed")
    works = sum(1 for c in kb.cases if c["outcome"] == "worked")
    check(f"failure-heavy corpus ({fails} failed / {works} worked)", fails / max(works, 1) >= 0.4)

    regions = {c["region"] for c in kb.cases}
    check(f"multi-region corpus ({len(regions)} regions)", len(regions) >= 5)

    print("\nCorpus integrity — schema discipline")
    bad_lesson = [c["id"] for c in kb.cases if len(c["key_lesson"]) < 30]
    check("no stub lessons", not bad_lesson, f"({bad_lesson})")
    check("cultural factors are lists", all(isinstance(c["cultural_factors"], list) for c in kb.cases))


# ---------------------------------------------------------------------------
# 3. Retrieval quality
# ---------------------------------------------------------------------------
def test_retrieval() -> None:
    print("\nRetrieval")
    kb = KnowledgeBase()
    cases = kb.find_cases("mobile money payments for people without bank accounts", top_k=3)
    check("fintech/trust query retrieves cases", bool(cases))
    check("M-Pesa surfaces for mobile money", any("m-pesa" in c["id"] for c in cases),
          f"(got {[c['id'] for c in cases]})")

    cases = kb.find_cases("exporting packaged food to a foreign supermarket chain", top_k=4, prefer_region="Europe")
    check("food-export query retrieves localisation cases",
          any("localis" in " ".join(c["tags"]) or "market-entry" in c["tags"] for c in cases),
          f"(got {[c['id'] for c in cases]})")

    cases = kb.find_cases("grocery delivery", top_k=3)
    check("failure records are retrievable", any(c["outcome"] == "failed" for c in cases))

    cases = kb.find_cases("VR arcade for families in Riyadh", top_k=3, prefer_country="Saudi Arabia",
                          prefer_region="Middle East")
    check("regional affinity ranks the local case first",
          cases and cases[0]["id"] == "saudi-cinema-reopening-2018",
          f"(got {[c['id'] for c in cases]})")

    patterns = kb.find_patterns("no money to start, need customers who already trust someone", top_k=3)
    check("patterns retrieved for a trust/distribution query", bool(patterns), f"(got {[p['id'] for p in patterns]})")

    check("empty query is handled", kb.find_cases("") == [])


# ---------------------------------------------------------------------------
# 4. Risk flags
# ---------------------------------------------------------------------------
def test_flags() -> None:
    print("\nRisk flags")
    oracle = IdeaOracle(brain=OfflineBrain())

    rep = oracle.analyze("cash only grocery store in Japan", country="Japan")
    titles = " ".join(f["title"] for f in rep.flags)
    check("high uncertainty avoidance flagged for Japan (UAI 92)", "uncertainty" in titles.lower())
    rep_in = oracle.analyze("a B2B service in India", country="India")
    check("power distance flagged for a high-PDI market (India 77)",
          any("power distance" in f["title"].lower() for f in rep_in.flags))

    rep = oracle.analyze("I have no money to start a business", country="Australia")
    check("zero-budget flagged", any("capital" in f["title"].lower() for f in rep.flags))

    rep = oracle.analyze("a subscription vitamin box delivered monthly in Indonesia", country="Indonesia")
    check("subscription affordability flagged for a price-sensitive market",
          any("subscription" in f["title"].lower() for f in rep.flags))
    check("cash/payment-rail flag present", any("payment" in f["title"].lower() for f in rep.flags))

    rep = oracle.analyze("hardware device for restaurants in Germany", country="Germany")
    check("capital intensity flagged for hardware", any("capital" in f["title"].lower() for f in rep.flags))


# ---------------------------------------------------------------------------
# 5. End-to-end report contract
# ---------------------------------------------------------------------------
def test_report() -> None:
    print("\nReport contract")
    oracle = IdeaOracle(brain=OfflineBrain())
    rep = oracle.analyze("home-cook food delivery in Jakarta, cash on delivery, no budget", country="Indonesia")

    md = rep.markdown
    for section in ("## 1. Reality check", "## 2. Does it fit the culture?", "## 3. What worked elsewhere",
                    "## 4. What killed the lookalikes", "## 6. Risk flags", "## 8. Your 7-day, $0 validation plan",
                    "## 9. Kill criteria", "## 10. What to verify before spending a dollar",
                    "Sources used in this report"):
        check(f"section present: {section}", section in md)

    check("survivorship-bias warning is in the header", "survivorship bias" in md.lower())
    check("sources section is code-generated, not model-generated", "Full dataset provenance" in md)
    check("evidence ids are reported", bool(rep.to_dict()["evidence_ids"]["worked"]))

    # the no-LLM path must never be empty
    check("offline report is substantial", len(md) > 4000, f"({len(md)} chars)")

    print("\nReport contract — branding")
    check("report is titled 'Arthabodh'", md.startswith("# Arthabodh —"), f"(got {md[:40]!r})")
    check("report credits Sarathi Labs", "Sarathi Labs" in md)
    check("report names the Shodh engine", "Shodh engine" in md)
    check("report carries the Arthashastra lineage", "Arthashastra" in md)
    check("Shodh summary reports case + market counts",
          "case files" in md and "markets" in md)

    print("\nReport contract — input hygiene")
    rep = oracle.analyze("", country="")
    check("empty idea does not crash", "## 1. Reality check" in rep.markdown)
    rep = oracle.analyze("a" * 5000, country="Nowhere")
    check("very long garbage input does not crash", "## 1. Reality check" in rep.markdown)
    rep = oracle.analyze("idea for a market not in the corpus", country="Peru")
    check("unknown country degrades gracefully", "## 1. Reality check" in rep.markdown)


if __name__ == "__main__":
    print("=" * 68)
    print("Arthabodh · Sarathi Labs — regression tests (stdlib only, offline)")
    print("=" * 68)
    test_intake()
    test_corpus()
    test_retrieval()
    test_flags()
    test_report()
    print("\n" + "=" * 68)
    print(f"RESULT: {PASS} passed, {FAIL} failed")
    print("=" * 68)
    sys.exit(1 if FAIL else 0)
