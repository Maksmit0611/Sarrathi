"""
agent.py — Arthabodh: the product core of Sarathi Labs.

Brand architecture (see docs/BRAND.md):
    Sarathi Labs   the lab / company
    Arthabodh      the product the user receives            <- this pipeline
    Shodh          the retrieval + reasoning engine inside it
    Arthashastra   the narrative lineage (Kautilya)

The pipeline is deliberately boring:

    INTAKE  ->  RETRIEVE  ->  PACK  ->  REASON  ->  REPORT
      |           |            |         |           |
   parse the   culture +   build the   LLM if   markdown with
   idea into   case files  grounded    available, citations to
   structure   + patterns  evidence    else rules every claim

The model NEVER answers from its own memory. It only sees retrieved, cited
evidence (a "context pack"), and its job is to reason over that evidence. That
is what stops the classic failure mode of an AI business advisor: confident,
generic, unverifiable advice.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import date

from .brain import Brain, OfflineBrain, get_brain
from .retrievers import KnowledgeBase

MAX_EVIDENCE_CHARS = 9000  # keeps the prompt inside free-tier token budgets


# ---------------------------------------------------------------------------
# 1. INTAKE — turn free text into structure
# ---------------------------------------------------------------------------
@dataclass
class IdeaBrief:
    raw: str
    country: str = ""
    sector: str = ""
    model_hint: str = ""
    stage: str = "idea"          # idea | existing_business | expanding
    budget: str = "unknown"      # none | small | medium | large
    keywords: list[str] = field(default_factory=list)
    countries_mentioned: list[str] = field(default_factory=list)


CITY_TO_COUNTRY = {
    "melbourne": "Australia", "sydney": "Australia", "brisbane": "Australia", "perth": "Australia",
    "auckland": "New Zealand", "wellington": "New Zealand",
    "mumbai": "India", "delhi": "India", "bangalore": "India", "bengaluru": "India", "chennai": "India",
    "hyderabad": "India", "kolkata": "India", "pune": "India",
    "jakarta": "Indonesia", "surabaya": "Indonesia", "bali": "Indonesia",
    "riyadh": "Saudi Arabia", "jeddah": "Saudi Arabia",
    "dubai": "United Arab Emirates", "abu dhabi": "United Arab Emirates",
    "naples": "Italy", "milan": "Italy", "rome": "Italy", "turin": "Italy",
    "nairobi": "Kenya", "mombasa": "Kenya",
    "lagos": "Nigeria", "abuja": "Nigeria",
    "london": "United Kingdom", "manchester": "United Kingdom", "birmingham": "United Kingdom",
    "new york": "United States", "san francisco": "United States", "los angeles": "United States",
    "chicago": "United States", "austin": "United States", "seattle": "United States",
    "tokyo": "Japan", "osaka": "Japan",
    "shanghai": "China", "beijing": "China", "shenzhen": "China", "guangzhou": "China",
    "sao paulo": "Brazil", "são paulo": "Brazil", "rio de janeiro": "Brazil",
    "mexico city": "Mexico", "guadalajara": "Mexico",
    "paris": "France", "lyon": "France", "berlin": "Germany", "munich": "Germany", "hamburg": "Germany",
    "stockholm": "Sweden", "singapore": "Singapore",
}

COUNTRY_SYNONYMS = {
    "usa": "United States", "us": "United States", "america": "United States",
    "uk": "United Kingdom", "britain": "United Kingdom", "england": "United Kingdom",
    "uae": "United Arab Emirates", "dubai": "United Arab Emirates", "abu dhabi": "United Arab Emirates",
    "aus": "Australia", "aussie": "Australia", "nz": "New Zealand",
    "sa": "Saudi Arabia", "ksa": "Saudi Arabia", "u.s.": "United States",
}

SECTOR_HINTS = {
    "fintech": ["fintech", "payment", "payments", "lending", "loan", "bank", "banking", "wallet", "insurance",
                "credit", "crypto", "savings", "save money", "mobile money", "remittance", "transfer money",
                "microfinance", "buy now pay later", "bnpl", "invoice"],
    "food": ["restaurant", "cafe", "coffee", "food", "bakery", "biscuit", "kitchen", "catering", "juice",
             "grocery", "meal", "cloud kitchen", "snack", "beverage", "tea", "dairy", "spice"],
    "retail": ["shop", "store", "retail", "boutique", "ecommerce", "e-commerce", "marketplace", "dropship",
               "supermarket", "franchise", "clothing", "apparel"],
    "education": ["school", "course", "tutor", "education", "training", "academy", "learning", "bootcamp", "exam"],
    "health": ["health", "clinic", "fitness", "gym", "wellness", "therapy", "medical", "pharmacy",
               "dental", "mental health", "nutrition"],
    "software": ["app", "software", "saas", "platform", "ai", "agent", "website", "tool", "automation",
                 "dashboard", "analytics"],
    "services": ["service", "consulting", "agency", "cleaning", "repair", "logistics", "delivery",
                 "laundry", "beauty", "salon", "rental", "booking"],
    "manufacturing": ["manufacturing", "factory", "craft", "handmade", "textile", "furniture", "hardware",
                      "device", "machine", "packaging", "assembly"],
    "tourism": ["tourism", "travel", "hotel", "tour", "experience", "entertainment", "event", "escape room",
                "gaming", "arcade", "cinema", "hostel"],
    "agriculture": ["farm", "farmer", "farming", "agriculture", "dairy", "organic", "agritech", "livestock",
                    "crop", "irrigation", "aquaculture"],
}

BUDGET_HINTS = {
    "none": ["no money", "no budget", "zero budget", "zero money", "no capital", "no funding",
             "no investment", "nothing to invest", "broke", "bootstrapped", "savings only",
             "not willing to invest", "don't have money", "dont have money", "cannot afford"],
    "small": ["small budget", "little money", "limited budget", "tight budget", "few thousand",
              "cheap", "low cost", "$500", "$1,000", "10k"],
    "medium": ["investment", "investors", "funding", "seed", "$50k", "$100k", "loan"],
    "large": ["vc", "venture", "series a", "millions", "$1m", "$10m"],
}


def parse_idea(text: str, kb: KnowledgeBase, country: str = "", budget: str = "") -> IdeaBrief:
    low = text.lower()
    brief = IdeaBrief(raw=text.strip())
    brief.country = country or ""
    brief.budget = budget or "unknown"

    if not brief.country:
        # Collect every country mentioned (full names + aliases) with positions.
        found: list[tuple[int, int, str]] = []
        for name in kb.all_countries():
            # word boundaries: "Australian wine" must not count as "Australia"
            for m in re.finditer(rf"\b{re.escape(name.lower())}\b", low):
                found.append((m.start(), m.end(), name))
        for alias, canonical in COUNTRY_SYNONYMS.items():
            for m in re.finditer(rf"\b{re.escape(alias)}\b", low):
                found.append((m.start(), m.end(), canonical))
        # cities count too - "a cafe in Melbourne" names a market
        for city, canonical in CITY_TO_COUNTRY.items():
            for m in re.finditer(rf"\b{re.escape(city)}\b", low):
                found.append((m.start(), m.end(), canonical))
        if found:
            found.sort()
            # Countries introduced by "from X" are the ORIGIN, not the target market.
            origins = {
                c for s, e, c in found
                if low[max(0, s - 6):s].strip().endswith("from")
            }
            # Earliest direction marker tells us where the action is pointing.
            marker_pos = None
            for marker in ("export", "expand", "launch", "sell", "open", "move to",
                           "scale", "enter", "targeting", "aimed at", "customers in", "market in"):
                idx = low.find(marker)
                if idx != -1 and (marker_pos is None or idx < marker_pos):
                    marker_pos = idx
            after = [c for s, e, c in found if marker_pos is not None and s > marker_pos and c not in origins]
            remaining = [c for s, e, c in found if c not in origins]
            if after:
                brief.country = after[0]           # first market named after "export to ..."
            elif remaining:
                brief.country = remaining[-1]      # otherwise the last place mentioned
            else:
                brief.country = found[0][2]
            brief.countries_mentioned = sorted({c for _, _, c in found})

    sector_scores = {s: sum(1 for w in words if w in low) for s, words in SECTOR_HINTS.items()}
    best_sector, best_score = max(sector_scores.items(), key=lambda kv: kv[1])
    brief.sector = best_sector if best_score else ""
    if not brief.country and not brief.sector and "tech" in low:
        brief.sector = "software"

    if brief.budget == "unknown":
        for level, words in BUDGET_HINTS.items():
            if any(w in low for w in words):
                brief.budget = level
                break

    if any(w in low for w in ("i already", "my business", "we run", "currently operate", "existing")):
        brief.stage = "existing_business"
    elif any(w in low for w in ("expand", "new market", "another country", "scale")):
        brief.stage = "expanding"

    brief.keywords = sorted(set(re.findall(r"[a-z]{4,}", low)))[:25]
    return brief


# ---------------------------------------------------------------------------
# 2 + 3. RETRIEVE and PACK
# ---------------------------------------------------------------------------
SECTOR_EXPANSION = {
    "food": "restaurant cafe food beverage menu taste localisation franchise supply chain export",
    "retail": "retail store shop marketplace ecommerce pricing store density localisation",
    "fintech": "payments lending wallet credit trust escrow agent network regulatory",
    "education": "school course training learning certification community",
    "health": "clinic health wellness regulation trust certification",
    "software": "software platform saas product-led freemium developer distribution",
    "services": "service delivery logistics marketplace informal workers supply",
    "manufacturing": "manufacturing factory cluster supplier quality export supply chain",
    "tourism": "travel tourism hospitality experience entertainment events",
    "agriculture": "farm agriculture cooperative dairy supply chain rural smallholder",
}


def build_evidence(brief: IdeaBrief, kb: KnowledgeBase) -> dict:
    query = " ".join([
        brief.raw,
        brief.sector,
        brief.country or "",
        SECTOR_EXPANSION.get(brief.sector, ""),
        "market entry" if brief.stage in ("expanding", "idea") else "",
    ])
    culture = kb.culture_profile(brief.country) if brief.country else None
    region = culture["region"] if culture else ""
    worked = kb.find_cases(query, top_k=4, outcome="worked", prefer_country=brief.country, prefer_region=region)
    failed = kb.find_cases(query, top_k=4, outcome="failed", prefer_country=brief.country, prefer_region=region)
    mixed = kb.find_cases(query, top_k=2, outcome="mixed", prefer_country=brief.country, prefer_region=region)
    patterns = kb.find_patterns(query + " " + (culture["business_notes"][:200] if culture else ""), top_k=4)
    return {"culture": culture, "worked": worked, "failed": failed, "mixed": mixed, "patterns": patterns}


def pack_to_text(ev: dict, brief: IdeaBrief) -> str:
    """Serialise retrieved evidence into the compact, cited block the LLM sees."""
    lines: list[str] = []
    lines.append(f"IDEA: {brief.raw}")
    lines.append(f"COUNTRY: {brief.country or 'not specified'} | SECTOR: {brief.sector or 'unclassified'}"
                 f" | STAGE: {brief.stage} | BUDGET: {brief.budget}")
    lines.append("")

    c = ev["culture"]
    if c:
        lines.append("== CULTURE PROFILE (source: data/cultures.csv; country-level averages, Hofstede-style dimensions) ==")
        lines.append(f"{c['country']} | PDI {c['pdi']} | IDV {c['idv']} | MAS {c['mas']} | UAI {c['uai']} | LTO {c['lto']} | IVR {c['ivr']}")
        lines.append(c["business_notes"])
        lines.append("")

    def block(title: str, cases: list[dict]) -> None:
        if not cases:
            return
        lines.append(f"== {title} ==")
        for cs in cases:
            lines.append(f"[{cs['id']}] {cs['name']} — {cs['country']}, {cs['era']}, {cs['sector']} "
                         f"(outcome: {cs['outcome']}, confidence: {cs['confidence']})")
            lines.append(f"  WORKED: {cs['what_worked']}")
            lines.append(f"  DIDN'T: {cs['what_didnt']}")
            lines.append(f"  CULTURE: {'; '.join(cs['cultural_factors'])}")
            lines.append(f"  LESSON: {cs['key_lesson']}")
        lines.append("")

    block("CASE FILES: WORKED", ev["worked"])
    block("CASE FILES: FAILED", ev["failed"])
    block("CASE FILES: MIXED", ev["mixed"])

    if ev["patterns"]:
        lines.append("== MODEL PATTERNS (source: data/patterns.json) ==")
        for p in ev["patterns"]:
            lines.append(f"[{p['id']}] {p['name']}: {p['essence']}")
            lines.append(f"  worked where: {'; '.join(p['worked_where'][:3])}")
            lines.append(f"  failed where: {'; '.join(p['failed_where'][:2])}")
            lines.append(f"  signals: {'; '.join(p['signals_you_need_it'][:3])}")
            lines.append(f"  first test: {p['first_test']}")
        lines.append("")

    text = "\n".join(lines)
    if len(text) > MAX_EVIDENCE_CHARS:
        text = text[:MAX_EVIDENCE_CHARS] + "\n[evidence truncated]"
    return text


# ---------------------------------------------------------------------------
# 4a. Heuristic risk flags (always run - these do not need an LLM)
# ---------------------------------------------------------------------------
def risk_flags(brief: IdeaBrief, ev: dict) -> list[dict]:
    flags: list[dict] = []
    c = ev["culture"]
    low = brief.raw.lower()

    def add(level: str, title: str, detail: str, evidence: str) -> None:
        flags.append({"level": level, "title": title, "detail": detail, "evidence": evidence})

    if c:
        uai = int(c["uai"])
        pdi = int(c["pdi"])
        idv = int(c["idv"])
        if uai >= 70:
            add("high", "High uncertainty avoidance — trust must be engineered",
                f"{c['country']} scores {uai} on uncertainty avoidance. Novel, unproven formats create friction: "
                "customers want guarantees, certification, refunds, trials and visible social proof before committing.",
                "Culture profile: UAI " + str(uai))
        if pdi >= 70:
            add("medium", "High power distance — gatekeepers decide",
                f"{c['country']} scores {pdi} on power distance. Deals often need a senior sponsor or a respected "
                "local partner; junior cold outreach will stall. Budget extra time for relationship-building before pricing talk.",
                "Culture profile: PDI " + str(pdi))
        if idv <= 40:
            add("medium", "Collectivist market — group and family drive purchase decisions",
                f"{c['country']} scores {idv} on individualism. Marketing that targets 'you alone' underperforms; "
                "design for family, community and shared use, and consider community-based distribution.",
                "Culture profile: IDV " + str(idv))
        if int(c["lto"]) <= 35:
            add("medium", "Short-term orientation — visible value fast",
                "This market rewards immediate, tangible benefit over long-horizon brand building. "
                "Lead with the result the customer sees in week one.",
                "Culture profile: LTO " + c["lto"])

    money_touching = any(w in low for w in (
        "payment", "pay", "checkout", "subscription", "monthly", "delivery", "ecommerce", "e-commerce",
        "online store", "shop online", "app store", "pre-order", "deposit", "invoice", "fee", "price"))
    if c and c.get("cash_heavy") == "1" and money_touching:
        add("high", "Payment rails — cash/mobile-money reality",
            f"{c['country']} is a cash-heavy market: {c['payment_rail']}. Card-only or auto-debit-only checkout "
            "will strangle conversion. Build cash-on-delivery, mobile money or agent-network payment in from day one, "
            "and price the collection cost into the unit economics.",
            f"Culture profile: payment_rail ({c['country']})")
    elif "cash" in low or "unbanked" in low or "no card" in low:
        add("high", "Payment rails", "Card/online-only checkout will strangle conversion in cash-first markets. "
            "Build cash-on-delivery, mobile-money or agent-network payment in from day one.",
            "Idea text mentions cash/absence of cards")
    if any(w in low for w in ("subscription", "monthly fee", "recurring")) and brief.budget != "large":
        add("medium", "Subscription affordability", "Recurring billing needs stable income and trust in auto-debit. "
            "In price-sensitive or cash-first markets, consider pre-paid bundles, sachet pricing or instalments instead.",
            "Idea uses a subscription model")
    if any(w in low for w in ("hardware", "machine", "device", "robot", "kitchen equipment")):
        add("high", "Capital intensity", "Physical product development consumes cash long before revenue and is brutally "
            "hard to reverse. Prototype with off-the-shelf parts and pre-orders before tooling anything.",
            "Idea appears to involve hardware")
    if any(w in low for w in ("delivery", "shipping", "last mile")) and any(w in low for w in ("per day", "low value", "cheap")):
        add("high", "Delivery unit economics", "Low-value, physically heavy items usually lose money per delivery until route "
            "density is high. Model cost-per-drop against density per km2 before buying vehicles.",
            "Idea combines delivery with low-value goods")
    if brief.budget == "none":
        add("high", "Zero capital constraint", "With no capital, you cannot buy distribution, inventory or attention. "
            "Your only available strategies are pre-sales, service-first (sell time before product), and partnering with "
            "someone who already owns the customer. Price the first 90 days to exactly $0.",
            "Stated budget: none")
    if any(w in low for w in ("regulated", "medical", "food safety", "financial advice", "children", "alcohol", "pharma")):
        add("high", "Regulatory exposure", "Licensing, labelling and liability can cost more than the product. "
            "Get the licence list and timeline before you build, not after.",
            "Idea touches a regulated category")

    if not any(f["title"] == "Cultural blind spot" for f in flags) and not c and brief.country == "":
        add("medium", "No target market specified", "Without a target country/culture, every recommendation is generic. "
            "Pick ONE beachhead market before testing anything.",
            "No country detected in the brief")

    return flags


# ---------------------------------------------------------------------------
# 4b. LLM reasoning (or rule-based synthesis if no brain)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are Arthabodh, the research product of Sarathi Labs, running on the Shodh engine. You are a business-idea analyst who reasons ONLY from supplied evidence.

NON-NEGOTIABLE RULES
1. Every factual claim must cite an evidence ID in square brackets, e.g. [m-pesa-2007-now] or [CULTURE].
   If the evidence does not support a claim, write "no evidence in corpus" instead of inventing one.
2. Never present a case study as a prediction. Say "this is a prior to test, not a guarantee".
3. Name the strongest argument AGAINST the user's idea. Flattery is failure.
4. Be concrete: names, numbers, currencies, weeks. No corporate filler.
5. If the idea is weak, say so plainly and explain what would have to be true for it to work.
6. Flag survivorship bias whenever you cite a success story.
7. Output valid markdown, no preamble, no closing pleasantries.

REPORT STRUCTURE (use these exact headings)
## 1. Reality check
## 2. Does it fit the culture?
## 3. What worked elsewhere (and why it might not work for you)
## 4. What killed the lookalikes
## 5. Model that fits your resources
## 6. Risk flags
## 7. Three adaptations for your market
## 8. Your 7-day, $0 validation plan
## 9. Kill criteria
## 10. What to verify before spending a dollar
"""


def llm_report(brief: IdeaBrief, evidence_text: str, flags: list[dict], brain) -> str:
    flag_text = "\n".join(f"- [{f['level'].upper()}] {f['title']}: {f['detail']}" for f in flags) or "- none generated"
    user_prompt = (
        f"{evidence_text}\n\n"
        f"== PRE-COMPUTED RISK FLAGS (already derived from the evidence) ==\n{flag_text}\n\n"
        f"Write the report for the idea above. Remember: cite evidence IDs, include the strongest argument "
        f"against the idea, and make section 8 executable this week with zero money."
    )
    return brain.chat(SYSTEM_PROMPT, user_prompt, temperature=0.4, max_tokens=2600)


def rule_based_report(brief: IdeaBrief, ev: dict, flags: list[dict]) -> str:
    """The no-LLM path. Assembles the same sections from the same evidence."""
    c = ev["culture"]
    out: list[str] = []

    out.append("## 1. Reality check")
    out.append(
        f"**Idea:** {brief.raw}\n\n**Market:** {brief.country or 'not specified'} · "
        f"**Sector:** {brief.sector or 'unclassified'} · **Stage:** {brief.stage} · **Budget:** {brief.budget}"
    )
    if c:
        out.append(
            f"\n**Shodh** (the research engine) ran without an LLM brain, so this Arthabodh is composed "
            f"directly from the corpus: **{len(ev['worked'])} comparable successes** and "
            f"**{len(ev['failed'])} comparable failures** for this idea in {c['country']}. "
            f"Read the failure column first — it is where the money is saved."
        )
    else:
        out.append("\nNo target country was detected in the brief, so the cultural analysis is limited. "
                   "Add a target market for a sharper read.")

    if c:
        out.append("\n## 2. Does it fit the culture?")
        out.append(
            f"| Dimension | Score | What it means for this idea |\n|---|---|---|\n"
            f"| Power distance | {c['pdi']} | {'Expect gatekeepers; a senior sponsor opens doors.' if int(c['pdi']) >= 70 else 'Relatively flat access; direct outreach can work.'} |\n"
            f"| Individualism | {c['idv']} | {'Decisions are family/group-driven; design for shared use.' if int(c['idv']) <= 40 else 'Individual choice dominates; persona-based targeting works.'} |\n"
            f"| Masculinity | {c['mas']} | {'Competition, status and scale framing land well.' if int(c['mas']) >= 60 else 'Quality-of-life, sustainability and care framing land well.'} |\n"
            f"| Uncertainty avoidance | {c['uai']} | {'Novelty creates friction — guarantees, trials and certification are required.' if int(c['uai']) >= 70 else 'Experimentation is tolerated; being first is an asset.'} |\n"
            f"| Long-term orientation | {c['lto']} | {'Patient brand-building works; relationships compound.' if int(c['lto']) >= 60 else 'Show tangible value in week one or lose the customer.'} |\n"
            f"| Indulgence | {c['ivr']} | {'Aspiration, celebration and enjoyment are strong purchase drivers.' if int(c['ivr']) >= 60 else 'Restraint; emphasise durability, value and duty.'} |"
        )
        out.append(f"\n> {c['business_notes']}")

    if ev["worked"]:
        out.append("\n## 3. What worked elsewhere (and why it might not work for you)")
        for cs in ev["worked"]:
            out.append(f"**{cs['name']}** — {cs['country']}, {cs['era']} · `[{cs['id']}]` · confidence: {cs['confidence']}")
            out.append(f"- Worked: {cs['what_worked']}")
            out.append(f"- Lesson: {cs['key_lesson']}")
            out.append(f"- ⚠️ Survivorship bias: you are reading the winner. Thousands of near-identical attempts are not in any dataset.\n")

    if ev["failed"]:
        out.append("## 4. What killed the lookalikes")
        for cs in ev["failed"]:
            out.append(f"**{cs['name']}** — {cs['country']}, {cs['era']} · `[{cs['id']}]`")
            out.append(f"- Killed by: {cs['what_didnt']}")
            out.append(f"- Cultural factor: {'; '.join(cs['cultural_factors'])}\n")

    if ev["patterns"]:
        out.append("## 5. Model that fits your resources")
        for p in ev["patterns"]:
            out.append(f"- **{p['name']}** (`[{p['id']}]`) — {p['essence']}")
            out.append(f"  - Fits when: {'; '.join(p['signals_you_need_it'][:2])}")
            out.append(f"  - First test: {p['first_test']}")

    out.append("\n## 6. Risk flags")
    if flags:
        for f in flags:
            icon = {"high": "🔴", "medium": "🟠", "low": "🟢"}.get(f["level"], "•")
            out.append(f"- {icon} **{f['title']}** — {f['detail']} _({f['evidence']})_")
    else:
        out.append("- No structural risk flags detected from the brief. That usually means the brief is too vague — add country, budget and business model.")

    out.append("\n## 7. Three adaptations for your market")
    if c:
        out.append(f"1. **Distribution** — reach customers the way {c['country']} already buys, not the way your competitors advertise.")
        out.append(f"2. **Trust** — {('build guarantees, certification and refunds into the product.' if int(c['uai']) >= 70 else 'move fast and publish openly; early adopters will reward speed.')}")
        out.append(f"3. **Pricing** — {('design for price sensitivity and instalments/sachets.' if int(c['ivr']) < 60 else 'design for aspiration; bundle and upsell.')}")

    out.append("\n## 8. Your 7-day, $0 validation plan")
    out.append("| Day | Action | Cost | Pass condition |\n|---|---|---|---|")
    out.append("| 1 | Write the one-sentence promise a stranger would repeat. | $0 | 5 people repeat it back correctly |")
    out.append("| 2 | Interview 5 people who are ALREADY spending money on the closest alternative. | $0 | 3 describe the alternative's flaw unprompted |")
    out.append("| 3 | Build the ugliest possible version (landing page, WhatsApp group, one manual delivery). | $0 | — |")
    out.append("| 4–5 | Try to take a pre-order or deposit from 20 strangers. | $0 | 2 pay before delivery |")
    out.append("| 6 | Deliver manually to those 2 and measure time + true cost per delivery. | $0–small | Cost per unit known within 20% |")
    out.append("| 7 | Decide: continue, pivot the customer, or kill. Write the reason down. | $0 | Decision written, with numbers |")

    out.append("\n## 9. Kill criteria")
    out.append("- You cannot name the specific person who will pay, or what they spend today on the alternative.")
    out.append("- Nobody pays anything (not even a deposit) in 7 days after seeing a real offer.")
    out.append("- Your true cost per unit is above what the market already pays for the alternative, with no path to close the gap in 3 months.")
    out.append("- The purchase requires behaviour change bigger than 'swap brand' — i.e. the customer must learn something new, buy new hardware, or change a habit tied to family or religion.")

    out.append("\n## 10. What to verify before spending a dollar")
    out.append("- Confirm the licence and tax requirements for this sector in your target market.")
    out.append("- Confirm the cultural dimensions against the primary source (Hofstede Insights data matrix) — the local copy here is a demo subset.")
    out.append("- Confirm every case study claim against its primary source; these are compressed post-mortems, not fresh research.")
    out.append("- Ask: who already tried this here, and can I find their customers?")

    return "\n".join(out)


# ---------------------------------------------------------------------------
# 5. REPORT
# ---------------------------------------------------------------------------
@dataclass
class Report:
    brief: IdeaBrief
    evidence: dict
    flags: list[dict]
    markdown: str
    brain_label: str

    def to_dict(self) -> dict:
        return {
            "brief": asdict(self.brief),
            "flags": self.flags,
            "brain": self.brain_label,
            "markdown": self.markdown,
            "evidence_ids": {
                "worked": [c["id"] for c in self.evidence["worked"]],
                "failed": [c["id"] for c in self.evidence["failed"]],
                "patterns": [p["id"] for p in self.evidence["patterns"]],
            },
        }


class IdeaOracle:
    def __init__(self, data_dir=None, brain=None):
        self.kb = KnowledgeBase(data_dir) if data_dir else KnowledgeBase()
        self.brain = brain if brain is not None else get_brain()

    def analyze(self, idea_text: str, country: str = "", budget: str = "") -> Report:
        brief = parse_idea(idea_text, self.kb, country=country, budget=budget)
        ev = build_evidence(brief, self.kb)
        flags = risk_flags(brief, ev)

        if isinstance(self.brain, OfflineBrain) or self.brain is None:
            body = rule_based_report(brief, ev, flags)
            brain_label = "Offline (rules + retrieval, no LLM)"
        else:
            try:
                body = llm_report(brief, pack_to_text(ev, brief), flags, self.brain)
                brain_label = f"{self.brain.label} [{self.brain.model}]"
            except Exception as exc:  # noqa: BLE001 - graceful degradation is a feature
                body = rule_based_report(brief, ev, flags)
                brain_label = f"Offline fallback (LLM error: {type(exc).__name__})"

        title_seed = " ".join(brief.raw.split())
        short_title = (title_seed[:72] + "…") if len(title_seed) > 72 else title_seed
        header = (
            f"# Arthabodh — {short_title}\n\n"
            f"*Sarathi Labs · engineered by **Shodh** · {date.today().isoformat()} · brain: {brain_label}*\n\n"
            f"> ⚠️ **Read this first.** The cultural scores are country-level averages, not individuals. "
            f"The case files are compressed post-mortems with survivorship bias built in. Nothing here is a prediction — "
            f"it is a set of priors and tests. Verify every claim against the primary sources listed in `data/README.md` "
            f"before you spend money.\n\n---\n\n"
        )
        sources = self._sources_section(ev)
        return Report(brief=brief, evidence=ev, flags=flags,
                      markdown=header + body + "\n\n---\n\n" + sources, brain_label=brain_label)

    @staticmethod
    def _shodh_summary(ev: dict) -> str:
        """One line proving the report is retrieval-grounded, not model-invented."""
        cases = ev["worked"] + ev["failed"] + ev["mixed"]
        regions = sorted({c["region"] for c in cases})
        markets = len({c["country"] for c in cases})
        return (f"**Shodh engine** retrieved **{len(cases)} case files** across **{markets} markets** "
                f"({', '.join(regions) if regions else 'region not determined'}) and "
                f"**{len(ev['patterns'])} model patterns**.")

    @staticmethod
    def _sources_section(ev: dict) -> str:
        lines = ["## Sources used in this report", "",
                 IdeaOracle._shodh_summary(ev), ""]
        c = ev["culture"]
        if c:
            lines.append(f"- Culture profile: `data/cultures.csv` → {c['country']} (demo subset; verify at geerthofstede.com)")
        for key, label in (("worked", "Success cases"), ("failed", "Failure cases"), ("mixed", "Mixed cases")):
            for cs in ev[key]:
                lines.append(f"- {label}: `{cs['id']}` — {cs['name']} ({cs['source_type']})")
        for p in ev["patterns"]:
            lines.append(f"- Pattern: `{p['id']}` — {p['name']} (`data/patterns.json`)")
        lines.append("")
        lines.append("Full dataset provenance, licences and primary-source links: `data/README.md`.")
        lines.append("")
        lines.append("*Arthabodh is a product of **Sarathi Labs**. Processing by the **Shodh** engine, "
                     "in the **Arthashastra** tradition of Kautilya.*")
        return "\n".join(lines)


if __name__ == "__main__":
    oracle = IdeaOracle()
    demo = ("I want to open a specialty coffee chain in Melbourne, Australia. I have no money, "
            "just me and a bike for delivery. I want to do a subscription: people pay monthly and get "
            "coffee delivered to their office.")
    rep = oracle.analyze(demo)
    print(rep.markdown)
