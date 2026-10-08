# ☸ Arthabodh

<!-- README tags / badges -->
![tests](https://img.shields.io/badge/tests-140%20passing-brightgreen)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)
![cost](https://img.shields.io/badge/cost-%240%20to%20run-brightgreen)
![engine](https://img.shields.io/badge/engine-Shodh-ff9933)
![agent](https://img.shields.io/badge/runs%20as-agent-orange)
![licence](https://img.shields.io/badge/licence-Apache--2.0-blue)
![PRs](https://img.shields.io/badge/PRs-welcome-brightgreen)

### *by **Sarathi Labs** · research by the **Shodh** engine · in the **Arthashastra** tradition of Kautilya*

> **Shodh your idea. Get your Arthabodh.**

An **agent** that tells you whether a business idea fits a **culture** and what happened to the people
who already tried it — built to run at **$0**, with **zero dependencies**, grounded in **cited
evidence** instead of a model's memory.

**An app waits for someone to visit it. Sarathi runs.** It is a process on your machine with memory
that persists, tools it can actually use, and a schedule it can keep — not a website you open.

Put your idea in. Get your Arthabodh back: a cultural fit read, the cases that worked, the cases that
died, risk flags, and a 7-day plan that costs nothing to test.

---

## Naming

Four names, four jobs, nothing overlapping. Full detail in [`docs/BRAND.md`](docs/BRAND.md).

| Layer | Name | Meaning |
|---|---|---|
| Lab | **Sarathi Labs** | सारथि *sarathi* — **charioteer**. Krishna did not fight Arjuna's war; he held the reins and gave counsel at the moment of decision. |
| Product | **Arthabodh** | अर्थबोध — **understanding of artha**: of wealth *and* of meaning. अर्थ = that which one strives for (wealth · purpose · meaning); बोध = awakening into knowing. |
| Engine | **Shodh** | शोध — **search + refinement**, from √śudh, *to purify*. Clear away what is false; what remains is knowledge. |
| Lineage | **Arthashastra** | Kautilya's ancient treatise on trade, markets, risk and strategy — the subject matter of this product, written 2,300 years ago. |

The three names tell the user's journey in sequence: **the idea is Shodh'd → the user receives their
Arthabodh → Sarathi Labs steers, it does not claim to be the hero.**

---

## Run the agent

```bash
cd sarathi-labs
python3 agent.py                                             # interactive session
python3 agent.py "research a tiffin service in Bengaluru, no budget"   # one-shot
python3 agent.py --tools                                     # everything it can do
```

It remembers across sessions, calls tools on its own, and runs unattended:

```bash
python3 agent.py --queue "research a cafe in Dandenong"      # queue work
python3 agent.py --watch                                     # work the queue and exit (cron-ready)
bash scripts/agent_cron.sh install                           # every Monday, 08:00
```

Full guide: [`docs/AGENT.md`](docs/AGENT.md) · how to build your own:
[`docs/BUILDING_AN_AGENT.md`](docs/BUILDING_AN_AGENT.md)

---

## Run the engine directly

```bash
cd sarathi-labs
python3 server.py           # web UI at http://localhost:8000
```

No `pip install`. No build step. No API key. Standard library only.

```bash
python3 cli.py --demo                                              # a full Arthabodh in your terminal
python3 cli.py --idea "laundry pickup in Mumbai" --country India    # your own idea
python3 cli.py --idea "..." --out arthabodh.md --json               # save it
python3 cli.py --providers                                          # see the free brains
```

**Optional — switch on an LLM brain (still free).** Get a key from
[Groq](https://console.groq.com/keys) (fastest to set up), [Google AI Studio](https://aistudio.google.com/apikey)
or [OpenRouter](https://openrouter.ai/keys):

```bash
cp .env.example .env       # paste your key in
export $(grep -v '^#' .env | xargs)
python3 server.py
```

The app works identically without a key — the rule-based path assembles the same evidence into a
slightly less fluent report. Keys only make the prose better.

---

## How it works

```
INTAKE ──▶ RETRIEVE ──▶ PACK ──▶ REASON ──▶ REPORT
 free text   culture     cited     LLM if     your Arthabodh:
   ↓          profile     evidence  available,  markdown +
country,      + case      block     else rules  full provenance
sector,       files +     (9k
budget        patterns    chars)
                    ▲
              the Shodh engine
```

The model **never answers from memory**. It only reasons over retrieved, cited evidence, and the
source list is generated in code. That is what stops an AI business advisor from producing
confident, generic, unverifiable advice.

| File | Role |
|---|---|
| `idea_oracle/brain.py` | Plug-in brains: Groq, Gemini, OpenRouter, NVIDIA, Mistral, local Ollama, or offline rules |
| `idea_oracle/retrievers.py` | The Shodh engine: TF-IDF retrieval, query expansion, field/region boosting, knowledge loader |
| `idea_oracle/agent.py` | Arthabodh: parse → retrieve → pack → reason → report + risk flags |
| `server.py` | Web UI + JSON API, standard library only |
| `cli.py` | Terminal interface |
| `data/` | 19 market profiles · 47 case files · 14 model patterns (licences in `data/README.md`) |
| `skills/` | Three Agent Skills (Claude Code / Cursor / Codex / Copilot) |
| `docs/CONCEPT.md` | The idea: problem, users, what makes it different, honest limits |
| [`docs/AGENT.md`](docs/AGENT.md) | How to run the agent: commands, memory layout, cron, MCP, extending it. |
| [`docs/BUILDING_AN_AGENT.md`](docs/BUILDING_AN_AGENT.md) | How to build an agent from scratch: the loop, tool calling, memory tiers, MCP, autonomy, safety. |
| `docs/SHODH.md` | The analysis engine — stages, retrieval design, risk flags |
| `docs/BRAND.md` | The naming architecture and usage rules |
| `docs/NAMING.md` | The research behind the name — 32 Sanskrit-rooted candidates |
| `docs/ROADMAP.md` | The 4-week, $0 plan from this repo to a deployed product |

> **Note on the Python package:** it is still imported as `idea_oracle` — a deliberate choice, so
> imports stay stable across the rename. Both class names work: `IdeaOracle` and `Arthabodh`.

## Install the skills (the token-efficient part)

The `skills/` folder holds three [Agent Skills](https://www.skills.sh) that make a coding agent better
at this work — and cheaper, because skills load progressively (~100 tokens at startup; detail on demand):

| Skill | Use it for |
|---|---|
| `culture-scout` | "Will this work in <country>?" — cultural fit analysis with the four hard entry checks |
| `case-file-analyst` | Turn any post-mortem/article/filing into a schema-valid case file for the corpus |
| `idea-oracle-builder` | Extend, debug and deploy the agent; includes free-stack and token-economy references |

```bash
# Claude Code
mkdir -p ~/.claude/skills && cp -r skills/* ~/.claude/skills/

# Cursor-style project skills
cp -r skills/* .cursor/skills/ 2>/dev/null || true

# Third-party skills (needs Node)
npx skills add https://github.com/juliusbrussee/caveman --skill caveman   # ~75% fewer output tokens
npx skills add vercel-labs/skills --skill find-skills                     # discover more skills
npx skills add mattpocock/skills --skill tdd --skill diagnosing-bugs --skill code-review
```

## The API

```bash
curl http://localhost:8000/api/health
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"idea":"home-cook food delivery in Jakarta, cash on delivery","country":"Indonesia","mode":"offline"}'
```

`/api/health` returns the brand and corpus stats:
```json
{"ok":true,"product":"Arthabodh","lab":"Sarathi Labs","engine":"Shodh",
 "cases":47,"patterns":14,"cultures":19,"brain":"Offline (rules + retrieval, no LLM)"}
```

`/api/analyze` returns `{brief, flags[], brain, markdown, evidence_ids{}}` — every claim in
`markdown` traces back to an id.

## Tests

```bash
python3 tests/test_intake.py     # 56 regression tests, offline, deterministic, stdlib only
```

CI runs the suite on every push along with a check that enforces the stdlib-only promise
(`.github/workflows/ci.yml`).

## Extend it

```bash
# add your own research documents to the corpus
python scripts/ingest_corpus.py --input ~/my-research --out data/my_corpus.jsonl

# see every free dataset you can pull in, and check corpus balance
python scripts/fetch_data.py --list
python scripts/fetch_data.py --check
```

## Honest limitations — please read before trusting the output

1. **Post-mortems have survivorship bias.** For every documented success there are thousands of unrecorded failures. Case files are *priors to test*, never predictions. The `failed` records are the valuable half.
2. **Cultural scores are country-level averages, not people.** They describe a slice of formal-sector workers in a specific era, not any individual, and nations are not cultures. Use them to generate hypotheses; verify against primary sources (`data/README.md`).
3. **The corpus is a demo subset** — 47 case files across 7 regions. Deliberately failure-heavy and non-US-weighted, but small. The pipeline is the product; the data is the work.
4. **Free tiers change.** Providers retire models without notice (Groq retired Llama models in Aug 2026; GitHub Models shut down in Jul 2026). Keep two providers configured — `PROVIDERS` in `brain.py` exists for this.
5. **Not legal, tax or financial advice.** Verify licences and obligations in your own jurisdiction.

## Licence

Code: **Apache-2.0** (see `LICENSE`). Case-file and pattern compilations: CC BY 4.0.
Culture data: research use only — see `data/README.md`.

---

☸ **Sarathi Labs** · शो **Shodh** · **Arthabodh** अर्थबोध · *अर्थशास्त्र* tradition
