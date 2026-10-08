# Shodh — the analysis engine

> **शोध** *śodha* — from the root **√śudh**, *to purify, to make clear*.
> Two senses, both true of this engine: **search / investigation**, and **refinement** —
> clearing away what is false, so what remains is knowledge.

**Shodh** is the engine inside **Arthabodh**. It is the part that does the work: it takes a plain-English
business idea, finds the real evidence that bears on it, and hands that evidence to the reasoning step
in a form that can be cited. Everything else in this project is packaging.

---

## What Shodh is responsible for

| Stage | Job | Code |
|---|---|---|
| **1. Intake** | Turn free text into structure: country, sector, stage, budget | `idea_oracle/agent.py::parse_idea` |
| **2. Retrieve** | Find the culture profile, case files and model patterns that bear on the idea | `idea_oracle/retrievers.py` |
| **3. Pack** | Compress that evidence into a cited block inside a fixed token budget | `agent.py::pack_to_text` |
| **4. Flag** | Compute deterministic risk warnings from the evidence and the market data | `agent.py::risk_flags` |

Reasoning and reporting sit *after* Shodh, and depend on it entirely.

---

## Stage 1 — Intake

Shodh reads the idea the way a person would, not the way a parser would.

- **Countries** — full names, aliases (`UK`, `USA`, `UAE`), and **60+ cities** (`Melbourne` → Australia, `Bengaluru` → India, `Jakarta` → Indonesia). It also distinguishes an **origin** from a **target market**: in *"a bakery in Naples, Italy, exporting to Germany"*, the target is Germany, not Italy. Direction markers (`export`, `expand`, `launch`, `sell to`) resolve it.
- **Sectors** — 10 classes (fintech, food, retail, software, services, manufacturing, tourism, agriculture, education, health), scored by keyword hits rather than first-match.
- **Budget** — `none | small | medium | large`, including the natural phrasings: *"no budget"*, *"cannot afford"*, *"we have $5,000"*.
- **Stage** — `idea | existing_business | expanding`.

Everything downstream is shaped by this step. A wrong country means the whole report is about the wrong culture, which is why it is covered by 10 dedicated regression tests.

## Stage 2 — Retrieval

**Lexical retrieval, deliberately.** TF-IDF with cosine similarity, plus a stemmer, query expansion and
field boosting. No vector database, no embeddings, no API calls, no dependencies.

That is not a limitation — it is the correct engineering choice at this scale:

| Reason | Detail |
|---|---|
| **Entity queries need exact terms** | *"M-Pesa"*, *"Jollibee"*, *"cash on delivery"* — embeddings blur these into vague semantic neighbours. TF-IDF hits them precisely. |
| **Citations must be verifiable** | A citation to `[m-pesa-2007-now]` is either right or wrong. Nothing is fuzzy. |
| **Runs anywhere, instantly** | Pure Python. The whole corpus indexes in milliseconds, offline, on a laptop with no GPU. |
| **Embeddings don't pay off yet** | Below ~5,000 documents, well-chunked lexical retrieval beats vector search — and this corpus is 47 documents. |

Three techniques make it work better than naive keyword search:

1. **Query expansion** — a sector maps to the vocabulary that actually appears in relevant cases (`fintech` → *payments, escrow, agent network, trust, regulatory*), so an idea phrased in modern words still finds cases written in other words.
2. **Field boosting** — a hit in `tags`, `name`, `sector` or `country` outranks an incidental hit in prose.
3. **Regional affinity** — cases from the user's target region rank higher, because a decision made in Jakarta is more informative about Jakarta than one made in San Francisco. Cases from the named market are *always* considered, even when the phrasing doesn't overlap — a vague query must never hide the most relevant local precedent.

**The upgrade path, when you need it:** past ~5,000 chunks, swap in Chroma or pgvector with
`sentence-transformers` (`all-MiniLM-L6-v2`) running locally on CPU. Both are free. The interface
stays `search(query, top_k, kind) -> [(score, Document)]`, so nothing else changes.

## Stage 3 — Packing (the token budget)

`MAX_EVIDENCE_CHARS = 9000`.

Whatever the corpus grows to, the model only ever sees a capped, compressed, **cited** evidence block:
case ids, outcomes, confidence levels, what worked, what didn't, the cultural mechanism, the lesson.
No raw JSON, no full articles, no duplicate records.

Free LLM tiers have token limits and the context window is a shared resource. Capping the evidence
here means a bigger corpus makes the answers *better*, not the bills *larger*.

## Stage 4 — Risk flags (computed, not generated)

Eight deterministic checks run **before** any LLM sees the idea. They are rules over the market data
and the brief, so the sharpest warnings never depend on a model remembering to mention them:

| Flag | Fires when |
|---|---|
| **High uncertainty avoidance** | market UAI ≥ 70 — novelty needs guarantees, trials, certification |
| **High power distance** | market PDI ≥ 70 — deals need a senior sponsor, not cold outreach |
| **Collectivist market** | market IDV ≤ 40 — the family/group decides, not the individual |
| **Short-term orientation** | market LTO ≤ 35 — value must be visible in week one |
| **Payment rails** | market is cash-heavy *and* the idea touches money → cash-on-delivery, mobile money or agent networks from day one |
| **Subscription affordability** | recurring billing in a price-sensitive or irregular-income market |
| **Capital intensity** | the idea involves hardware, machines or devices |
| **Regulatory exposure** | health, finance, food safety, children, alcohol, pharma |
| **Zero capital** | budget is `none` — only pre-sales, service-first and partners remain |
| **No target market** | nothing identifiable — every recommendation would be generic |

These are the same four hard checks a good consultant runs: **trust, payment rail, decision unit,
legitimacy** — expressed as data lookups instead of intuition.

---

## What Shodh deliberately does not do

| Not this | Why not |
|---|---|
| **Predict success** | Nobody can, and claiming otherwise is how these tools lose trust. Shodh surfaces *priors and tests*. |
| **Generate the source list** | Sources are produced in code from the retrieved ids. A model that writes its own citations can invent them; Shodh makes that impossible. |
| **Answer from model memory** | The LLM only sees the packed evidence and reasons over it. If the corpus is silent, the right answer is *"no evidence in corpus"* — not a plausible guess. |
| **Use global averages as if they were individuals** | Cultural scores are country-level central tendencies. Shodh reports them as hypotheses and requires the caveat in every report. |
| **Flatter the user** | Every report must state the strongest argument against the idea. An advisor that only agrees is a mirror with the lights off. |

---

## Design principles

1. **Retrieval before generation.** Evidence first; prose second. Every bug in output quality is investigated from the evidence block backwards.
2. **Everything is citable.** If a fact cannot be traced to a file and an id, it does not belong in a report.
3. **Degrade gracefully.** No API key, no internet, no money — Shodh still produces a complete, useful, rule-based report. The LLM is an upgrade, never a dependency.
4. **Failure-weighted evidence.** For every two success cases there is at least one failure. Failures are the valuable half: they are where the money is saved and where every other dataset is thin.
5. **No dependencies.** Python's standard library only. The promise is enforced by CI on every push.

---

## Extending Shodh

```bash
# add your own research documents to the corpus
python scripts/ingest_corpus.py --input ~/my-research --out data/my_corpus.jsonl

# see available free datasets, and check corpus balance
python scripts/fetch_data.py --list
python scripts/fetch_data.py --check     # outcome / confidence / region distribution
```

To add a whole new kind of evidence (regulations, cost benchmarks, distribution channels):
load it in `KnowledgeBase._load`, index it in `_build_documents` with a new `kind`, add a
`find_<kind>` method, and wire it into `build_evidence`. Then add it to `_sources_section` —
**a source that cannot be cited must not be used.**

Full build instructions: `skills/idea-oracle-builder/SKILL.md`.
