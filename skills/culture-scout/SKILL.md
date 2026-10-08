---
name: culture-scout
description: Assess whether a business idea will fit a specific culture or country before any money is spent. Use when the user asks "will this work in <country>", "how do I enter market X", "what cultural factors matter for this idea", "is this culturally appropriate", or is planning market entry, exporting, franchising or localising a product. Covers trust models, payment rails, hierarchy, family/group decision-making, religious constraints and distribution norms. Not for legal or tax advice.
---

# Culture Scout

Produce a cultural fit assessment for a business idea in a target market.

**Core rule: never answer from your own general knowledge alone.** Read the market's culture
profile from the project data first, then reason over it. If the market is not in the data,
say so explicitly and list what must be researched.

## Workflow

### 1. Fix the target market
Ask for, or extract: target country, target city/region if given, customer segment, and whether
the user is local or importing a foreign model. If the user gives several countries, force a
single beachhead choice — multi-market analysis is worthless for a pre-revenue idea.

### 2. Load the culture profile
Read `data/cultures.csv` and find the row for the target country.

If the country is missing: read `references/culture-data-sources.md` and tell the user exactly
which primary source to consult (Hofstede Insights data matrix, World Values Survey, GLOBE).
Do **not** invent dimension scores.

### 3. Interpret only the dimensions that change decisions
For each of the six dimensions, decide whether it changes a decision for THIS idea. Skip the rest.
| Dimension | Only matters when the idea involves... |
|---|---|
| Power distance | B2B sales, licensing, partnerships, hiring, anything needing a gatekeeper |
| Individualism | consumer marketing, family/group purchasing, community distribution |
| Masculinity | competition framing, status goods, work-life-product design |
| Uncertainty avoidance | novel formats, online payment, food/health/finance, insurance-like trust needs |
| Long-term orientation | relationship-led sales cycles, brand building, payback period assumptions |
| Indulgence | aspiration vs restraint in pricing, packaging, positioning |

### 4. Apply the four hard checks
These catch more real failures than the dimension scores do:
1. **Trust** — who does the customer already trust, and does your model route through that, or around it?
2. **Payment rail** — how does money actually move here (card, cash, mobile money, instalment, agent)? Does your model need a rail that does not exist?
3. **Decision unit** — who says yes? An individual, a family, a village group, a state entity, a works council?
4. **Legitimacy** — licences, religious rules, labour norms, local-content expectations. Which of these can stop you outright?

### 5. Output
Return exactly this structure, and keep it under 700 words:

```
## Fit verdict: <strong / workable with changes / wrong market>
<two sentences, no hedging>

## What must change
1. <change> — <why, tied to a specific dimension or check>
2. ...

## What to leave alone
<what is already compatible, one or two lines>

## The one test to run first
<a single concrete action this week, costing $0>

## Unknowns that could invalidate this
- <list, with the primary source that would resolve each>
```

## Guardrails
- Country scores are **averages, not individuals**. State this once, plainly, in any output that cites scores.
- Never claim a culture "is" something. Write "the country-level average suggests" or "in this market the norm is often".
- Refuse to produce stereotypes about people. Talk about institutions, norms and transaction structures — never about character or intelligence of a population.
- Flag religious or legal constraints as constraints, without judgement.
- If the user's plan depends on changing a cultural norm to work, treat that as a red flag, not a marketing opportunity.

## References (load only when needed — progressive disclosure)
- `references/culture-data-sources.md` — where to get real dimension data, free, with licences
- `references/entry-checks.md` — the expanded checklist for each of the four hard checks
