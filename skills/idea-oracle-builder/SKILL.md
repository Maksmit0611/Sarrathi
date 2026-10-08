---
name: idea-oracle-builder
description: Build, extend or debug Arthabodh (Sarathi Labs) and similar retrieval-grounded research agents at zero cost. The Shodh engine retrieves cited evidence; the model only reasons over it. Use when the user wants to add a data source, swap the LLM brain, add a free API provider, upgrade retrieval to embeddings, deploy for free, reduce token costs, or turn a research corpus into an agent. Also use when debugging "the agent gives generic advice", "the agent hallucinates sources", or "my API costs are too high".
---

# Arthabodh Builder *(Sarathi Labs)*

Assemble and extend **Arthabodh** — a research agent that is grounded, auditable and $0 to run.

*Brand: **Sarathi Labs** (lab) · **Arthabodh** (product) · **Shodh** (engine) · **Arthashastra** (lineage). See `docs/BRAND.md`.*

**The architectural law of this project: the LLM never answers from memory. It only reasons over
retrieved, cited evidence.** Any change that violates this rule is a regression, no matter how
impressive the demo looks.

## The five-stage pipeline

```
INTAKE -> RETRIEVE -> PACK -> REASON -> REPORT
```
Keep this shape when extending. Each stage has one job:

| Stage | Job | Where it lives |
|---|---|---|
| Intake | free text -> structured brief (country, sector, budget, stage) | `idea_oracle/agent.py::parse_idea` |
| Retrieve | query -> scored, cited documents | `idea_oracle/retrievers.py` |
| Pack | documents -> compact evidence block within a token budget | `agent.py::pack_to_text` |
| Reason | LLM (if available) or rules (always available) | `agent.py::llm_report` / `rule_based_report` |
| Report | markdown + provenance list | `agent.py::IdeaOracle.analyze` |

## Common tasks

### Add a data source
1. Put the source in `data/` as JSON/CSV.
2. Add a loader in `retrievers.py::KnowledgeBase._load`.
3. Add documents in `_build_documents` with a `kind` (e.g. `"regulation"`).
4. Add a `find_<kind>` method and wire it into `agent.build_evidence`.
5. Add it to `_sources_section` so every claim shows provenance.
Rule: a source that cannot be cited must not be used.

### Swap the brain
One interface: `chat(system, user) -> str`. Any provider that speaks OpenAI-compatible chat
completions works. Add an entry to `PROVIDERS` in `brain.py` with `base_url`, `key_env`, `model`.
Verify the model id against the provider's live docs — free model ids change monthly.
See `references/free-stack.md` for current free tiers and their limits.

### Add a retrieval strategy
Keep the `search(query, top_k, kind) -> [(score, Document)]` contract. Add fields to the
`Document` dataclass (e.g. `payload`, `kind`) and boost/rerank in `KnowledgeBase.find_*`.
Retrieval upgrades that pay off, in order:
1. better **query expansion** (sector/region synonyms) — biggest win, zero cost
2. **field boosting** (tags/name/sector over prose) — done in `_boost`
3. **regional affinity** (prefer the user's region) — done in `find_cases`
4. embeddings, only past ~5,000 docs
Do these in order. Embeddings are the last resort, not the first idea.

### Reduce token cost
1. Enforce `MAX_EVIDENCE_CHARS` in `pack_to_text` — truncate evidence, never the instructions.
2. Send compressed evidence: ids and short fields only. Never send whole JSON files.
3. Use a small model for retrieval-side tasks (classification, tagging) and the big model only for synthesis.
4. Cache reports keyed on `hash(brief + evidence_ids)` so repeat queries cost $0.
5. Install the `caveman` skill for terse agent output (~75% fewer output tokens) — see `references/token-economy.md`.

### Debug "the agent gives generic advice"
Work the pipeline backwards:
1. Print `pack_to_text(ev, brief)` — is the evidence specific and non-empty?
2. If empty: retrieval failure -> check tokenisation, stemmer, `top_k`, and score threshold `> 0.02`.
3. If it has evidence but output is generic: prompt failure -> require citation per claim, and forbid unsupported statements.
4. If it cites nothing: pack failure -> the model is not seeing ids. Add ids as a prefix on every evidence line.

### Debug "the agent hallucinates sources"
- Make citation mandatory and check the output contains `[` before returning it. Reject and retry once.
- Never let the model write the source list. Generate the sources section in code (`IdeaOracle._sources_section`).
- Keep a whitelist of valid ids; strip any bracket reference not in the whitelist.

## Non-negotiable guardrails for any advisory agent
1. **Citation or silence** — unsupported claims are replaced with "no evidence in corpus".
2. **State the strongest counter-argument** in every report.
3. **Label bias** — survivorship bias on successes, averages-not-individuals on culture data.
4. **Confidence per record** and per claim; never present `low` as fact.
5. **Refuse stereotypes** — describe institutions and structures, never a population's character.
6. **Graceful degradation** — the rule-based path must always produce a usable report.
7. **Never invent numbers** — `unknown` is a valid value.

## Definition of done for a new feature
- [ ] works with no API key (offline path intact)
- [ ] every new claim is traceable to a file + id in the sources section
- [ ] no new mandatory dependency without a documented reason
- [ ] token budget respected (`MAX_EVIDENCE_CHARS`)
- [ ] tested with one idea from a country that is NOT the user's own

## References (load only when needed)
- `references/free-stack.md` — free LLM providers, hosting, vector DBs, with current limits
- `references/token-economy.md` — how skills save tokens and how to measure it
- `references/sources-to-ingest.md` — where to get more culture and business-outcome data
