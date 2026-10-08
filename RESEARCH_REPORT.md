> **Naming note.** This research was written before the product was named. The agent described here is now
> **Arthabodh**, built by **Sarathi Labs**, with its retrieval engine called **Shodh** — see `docs/BRAND.md`.
> Older references to "the Idea Oracle" below refer to the same codebase; the Python package is still
> imported as `idea_oracle` for stability.

# Research report: building a culture-aware business-idea agent for $0

*Compiled 8 October 2026 · everything below is free, open-source, or has a genuine free tier.*

---

## 1. TL;DR — the stack to actually use

| Layer | Pick this | Why | Cost |
|---|---|---|---|
| **Brain (LLM)** | **Groq** (`openai/gpt-oss-120b`) as primary, **Gemini 2.5 Flash** as backup, **Ollama** offline as insurance | Fastest free tier, no credit card, OpenAI-compatible; Gemini gives a second generous quota | $0 |
| **Agent framework** | **None for v1.** Plain Python + a retrieved-evidence prompt. Add **LangGraph** only when you need branching/state | Frameworks add concepts you don't need yet; your bottleneck is evidence quality, not orchestration | $0 |
| **Retrieval** | **TF-IDF in pure Python** now → **Chroma + sentence-transformers** past ~5,000 docs | Exact-term matching beats embeddings on entity queries ("M-Pesa", "Jollibee") and needs zero setup | $0 |
| **Knowledge** | Your own case-file corpus + *Hofstede dimension data matrix* + *World Values Survey* + Kaggle startup-failure datasets + primary filings | Structured, citable, licence-tracked — this is the actual moat | $0 |
| **Skills** | `caveman` (‑75% output tokens), `find-skills`, `tdd`, `diagnosing-bugs`, `code-review`, `agent-browser`, plus the 3 custom skills in this repo | Progressive disclosure = hundreds of skills installed at ~100 tokens each | $0 |
| **Hosting** | Cloudflare Pages/Vercel (frontend) + Hugging Face Spaces or Render (backend); no DB needed at first | This app is stateless — it doesn't need a database or auth yet | $0 |
| **Learning** | NirDiamant's 5 repos, `microsoft/ai-agents-for-beginners`, `awesome-freellm-apis` | Runnable notebooks, not slides | $0 |

**The single most important decision:** build the **evidence corpus and the citation discipline** first.
The model is a commodity you can swap in an afternoon; a well-structured, failure-heavy, multi-region
case-file corpus is the part nobody else has. Everything in section 5 exists to make that cheap.

---

## 2. How to think about the build

Your idea has five separable problems. Solve them in this order; each one is independently testable.

```
 (1) INTAKE      what is the user actually asking?  country, sector, stage, budget
 (2) EVIDENCE    what do we know?                   culture profiles + case files + patterns
 (3) REASONING   what does it mean for them?        LLM over retrieved, cited evidence
 (4) DELIVERY    how do they use it?                web UI / CLI / chat
 (5) BUSINESS    who pays, and for what?            your call, but free tiers get you to 20 users
```

Two failure modes kill projects like this, and both are avoided by order of operations:

- **Building the interface before the evidence.** You end up with a beautiful wrapper on a generic chatbot.
- **Chasing "autonomous agents" before grounding.** Autonomy without evidence just produces confident nonsense faster.

Your specific product — *"people put in their business idea; the agent tells them what worked and what
didn't, across cultures"* — is fundamentally a **retrieval + structured-reasoning** problem,
not an orchestration problem. That is why v1 does not need CrewAI, AutoGen, or a multi-agent swarm.

---

## 3. The brain: which LLM to use when you have no budget

All of these are OpenAI-compatible, so one adapter switches between them (`idea_oracle/brain.py` already does).

| Provider | Good free model | Free limits (verify — they change monthly) | Card needed? |
|---|---|---|---|
| **Groq** ⭐ start here | `openai/gpt-oss-120b` | ~30 req/min, generous daily token cap, extremely fast | No |
| **Google Gemini** | `gemini-2.5-flash` | Generous free tier in AI Studio; Flash-Lite is faster | No |
| **OpenRouter** | any `:free` model (~19–30 rotating) | ~20 req/min, 50/day (1,000/day after a one-off $10) | No |
| **NVIDIA NIM** | `meta/llama-3.3-70b-instruct` | 120+ open models, free prototyping | No |
| **Mistral** | `mistral-small-latest` | Free experiment tier (phone verification) | No |
| **Cloudflare Workers AI** | `gpt-oss-120b` | ~10,000 Neurons/day | No |
| **Ollama (local)** | `llama3.1`, `qwen2.5`, `phi4` | Unlimited, offline, no key — needs your RAM | No |

Signup links: [console.groq.com/keys](https://console.groq.com/keys) ·
[aistudio.google.com/apikey](https://aistudio.google.com/apikey) ·
[openrouter.ai/keys](https://openrouter.ai/keys) · [build.nvidia.com](https://build.nvidia.com) ·
[ollama.com/download](https://ollama.com/download)

**Strategy: stack them.** 1,500 Gemini requests + 1,000 Groq + 1,000 OpenRouter ≈ 3,500 free
requests a day, which is far more than a prototype needs. Keep two providers configured at all
times — providers retire models without warning (Groq retired Llama 3.3 70B and 3.1 8B in
August 2026; Cerebras moved its free tier to a paid trial; GitHub Models shut down in July 2026).

**What to use each for:**

| Task | Model class | Reasoning |
|---|---|---|
| Classifying/tagging/deduping corpus records | small & fast (gpt-oss-20b, Flash-Lite, local 3B–8B) | high volume, low difficulty — never spend a big model here |
| Writing the final analysis | the biggest free model you can reach | this is the one place quality is visible to users |
| Offline / privacy-sensitive runs | Ollama | zero marginal cost, zero network dependency |

**Tracking to avoid:** a continuously-updated list of 134+ free LLM APIs lives at
[github.com/open-free-llm-api/awesome-freellm-apis](https://github.com/open-free-llm-api/awesome-freellm-apis).
Bookmark it; free rosters rotate.

---

## 4. The best repos for this build (ranked for *your* use case)

### 4a. Frameworks — and when you'd actually need them
| Repo | Stars (2026) | Use it when |
|---|---|---|
| [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | ~40–42K | you need stateful branching, checkpoints, human-in-the-loop approval between steps |
| [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI) | ~57–61K | you want role-based multi-agent teams (researcher / analyst / writer) |
| [agno-agi/agno](https://github.com/agno-agi/agno) | ~42–59K | you need high-concurrency agent fleets with built-in memory |
| [openai/openai-agents-python](https://github.com/openai/openai-agents-python) | ~29–42K | minimal primitives (agents, handoffs, guardrails) and you're fine with OpenAI-first |
| [pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai) | ~19K | you want typed, validated outputs — genuinely useful for structured case-file extraction |
| [huggingface/smolagents](https://github.com/huggingface/smolagents) | ~29K | you want the smallest auditable code-generating agent |
| [microsoft/agent-framework](https://github.com/microsoft/agent-framework) | ~28K | enterprise .NET/Python, graph workflows (AutoGen is now maintenance-only; AG2 is the community fork) |
| [google/adk-python](https://github.com/google/adk-python) | ~11K | Google Cloud / Gemini-native deployment |

**Recommendation for v1: use none of them.** Ship the 400 lines in this repo, learn what breaks,
then adopt LangGraph only if you add multi-step human approval. Frameworks are load-bearing once
you have state; before that they are indirection.

### 4b. Retrieval / RAG
| Repo | Why it matters |
|---|---|
| [NirDiamant/RAG_Techniques](https://github.com/NirDiamant/RAG_Techniques) (~30K ⭐) | 41 runnable techniques from chunking to agentic and graph RAG + an evaluation suite. The single best free RAG education. |
| [chroma-core/chroma](https://github.com/chroma-core/chroma) | local, embedded vector DB, Apache-2.0 — the upgrade path when you outgrow TF-IDF |
| [qdrant/qdrant](https://github.com/qdrant/qdrant) | production-grade, single Rust binary, rich filtering, free cloud tier |
| [run-llama/llama_index](https://github.com/run-llama/llama_index) (~52K) | when your data becomes documents, PDFs and heterogeneous sources |
| [deepset-ai/haystack](https://github.com/deepset-ai/haystack) (~26K) | production retrieval pipelines with strong evaluation tooling |
| [mem0ai/mem0](https://github.com/mem0ai/mem0) (~52K) | persistent memory across sessions once users have accounts |
| [explodinggradients/ragas](https://github.com/explodinggradients/ragas) | measure whether your retrieved evidence is actually good — do this before adding features |

### 4c. Agents + learning (all free, all runnable)
| Repo | Why |
|---|---|
| [NirDiamant/GenAI_Agents](https://github.com/NirDiamant/GenAI_Agents) (~25K ⭐) | 59 agent implementations, basic → multi-agent, in LangGraph/AutoGen/PydanticAI |
| [NirDiamant/agents-towards-production](https://github.com/NirDiamant/agents-towards-production) (~22K) | orchestration, memory, observability, evaluation, deployment, fine-tuning |
| [NirDiamant/Agent_Memory_Techniques](https://github.com/NirDiamant/Agent_Memory_Techniques) | 30 notebooks on agent memory: vector, graph, Mem0, Letta, Zep, Graphiti |
| [microsoft/ai-agents-for-beginners](https://github.com/microsoft/ai-agents-for-beginners) | free structured course, 10+ lessons |
| [aishwaryanr/awesome-generative-ai-guide](https://github.com/aishwaryanr/awesome-generative-ai-guide) | free courses incl. an agentic-AI crash course |
| [e2b-dev/awesome-ai-agents](https://github.com/e2b-dev/awesome-ai-agents) | the index of open-source agents when you need a specific capability |

### 4d. Ready-made agents you can study or self-host
| Repo | Note |
|---|---|
| [Dify](https://github.com/langgenius/dify) (~157K ⭐) | self-hostable LLM app platform with visual workflows + RAG. Fastest non-code path to *something*. Source-available licence (not OSI) — check before commercial use. |
| [Langflow](https://github.com/langflow-ai/langflow) (~155K) | MIT visual builder compiled to LangChain code |
| [RAGFlow](https://github.com/infiniflow/ragflow) (~91K) | deep-document RAG with grounded citations — good reference for citation design |
| [browser-use](https://github.com/browser-use/browser-use) (~86K) | browser automation for agents — relevant if you want the agent to go fetch evidence itself |
| [OpenHands](https://github.com/All-Hands-AI/OpenHands) (~84K) | autonomous coding agent; also a good architectural reference |
| [Mintplex-Labs/anything-llm](https://github.com/Mintplex-Labs/anything-llm) | private "chat with your documents" desktop app |

---

## 5. The knowledge layer — where your actual advantage is

This is the part most people skip, and it's the part that makes the product defensible.

### 5a. Culture and values (free, citable)
| Source | What you get | Licence |
|---|---|---|
| [Hofstede dimension data matrix](https://geerthofstede.com/research-and-vsm/dimension-data-matrix/) | 6 dimensions, ~100 countries, CSV/XLS | free for research; **commercial use requires permission** |
| [World Values Survey](https://www.worldvaluessurvey.org/WVSContents.jsp) | raw longitudinal microdata, 80+ countries since 1981 | openly available to researchers |
| GLOBE study | 9 dimensions, 60+ societies | published scores only; raw data not public |
| [World Bank Open Data](https://data.worldbank.org) | business conditions, connectivity, finance, CC BY 4.0 | CC BY 4.0 |
| Pew Research Global Attitudes | religion, family, gender, tech attitudes | free with citation |
| National statistics offices (ABS, ONS, BPS, NBS-Kenya…) | sector size, business survival rates, household spend | usually open |

### 5b. What worked / what didn't (the "case file" layer)
| Source | What it gives |
|---|---|
| [Kaggle — Startup Failures](https://www.kaggle.com/datasets/dagloxkankwanda/startup-failures) | 814 companies; 409 with 13 binary failure-cause flags (no budget, competition, poor market fit, platform dependency, regulatory pressure, overhype…) — **the best free labelled failure dataset** |
| [Kaggle — Crunchbase success/fail](https://www.kaggle.com/datasets/yanmaksi/big-startup-secsees-fail-dataset-from-crunchbase) | success/failure classification at scale |
| [Kaggle — Financial Distress](https://www.kaggle.com/datasets/shebrahimi/financial-distress) | quantitative distress features (Altman/Ohlson lineage) |
| [CB Insights post-mortem index](https://www.cbinsights.com/research/startup-failure-post-mortem/) | narrative failure taxonomy — use it to find *which* companies to write case files about |
| SEC EDGAR / ASX / Companies House / ASIC | primary filings — the source of truth for any outcome claim |
| Founders' own post-mortems, HBR, business-school case archives | mechanisms and causal detail |

### 5c. The method that makes this data usable
Raw articles are useless to an agent; **structured, cited records** are the product. The schema this
repo uses (see `skills/case-file-analyst/references/case-schema.md`) forces every record to carry:

`outcome` (worked / failed / mixed) · what worked · what didn't · **cultural factors as mechanisms, not traits** ·
transferable lesson · tags · **confidence level** · source type.

Three rules that matter more than volume:
1. **Failure-heavy corpora are better.** Aim for ≥1 failure record per 2 successes. Failures are where the money is saved and where every other dataset is thin.
2. **Multi-region or it's useless.** A corpus of US tech successes teaches nothing about Jakarta. Target ≥6 regions, ≥40 records.
3. **Track licences from ingestion, not later.** CC BY-NC data cannot ship in a commercial product. `data/README.md` exists for exactly this.

---

## 6. Skills and plugins — the token-efficiency layer you asked about

### 6a. What "skills" are now
Agent Skills are an open standard (originally Anthropic, standardised at agentskills.io, adopted by
26+ platforms including Claude Code, Cursor, Codex, GitHub Copilot, Gemini CLI, VS Code, Windsurf,
Zed, Cline, Goose, OpenCode). A skill is a folder with a `SKILL.md` (YAML frontmatter + markdown
instructions) plus optional `references/`, `scripts/`, `assets/`.

**[skills.sh](https://www.skills.sh) is the directory** — 1.2M+ installs tracked, with install
counts and security audits. Install with:

```bash
npx skills add <owner/repo>                                    # whole repo
npx skills add https://github.com/juliusbrussee/caveman --skill caveman   # one skill
```

### 6b. Why skills save tokens (progressive disclosure)
| Tier | Loads | When | Cost |
|---|---|---|---|
| 1 — metadata | name + description only | always, at startup | **~30–100 tokens per skill** |
| 2 — instructions | the `SKILL.md` body | only when triggered | ~1–5k tokens |
| 3 — resources | `references/`, `scripts/` | only when a step needs it | unlimited: **script code never enters context, only its output** |

That's why you can install 50 skills and still have a lean context. And it's why the writing rule is
**body = workflow, references = detail**. Measured effects reported by practitioners in 2026:
splitting a fat `SKILL.md` into body+references cut per-trigger tokens ~60%; one documented session
went from $3.60 → $2.64 and 17m → 9m wall time with 53% fewer tokens.

### 6c. Specific skills worth installing (from the skills.sh leaderboard)
| Skill | Installs | What it does for you |
|---|---|---|
| `vercel-labs/skills` → **find-skills** | 3.7M | discovers other skills — install this first, it's how you find the rest |
| `juliusbrussee/caveman` → **caveman** | 562K | **ultra-compressed output mode, ~75% fewer tokens**, technical accuracy preserved; auto-disables for security/irreversible actions |
| `mattpocock/skills` → **grill-me / grill-with-docs** | 1.3M / 1.1M | makes the agent interrogate your plan before it builds — cheap way to avoid building the wrong thing |
| `mattpocock/skills` → **tdd**, **diagnosing-bugs**, **code-review** | ~1M each | the daily dev loop: test-first, root-cause debugging, real review passes |
| `mattpocock/skills` → **domain-modeling**, **codebase-design**, **improve-codebase-architecture** | 0.7–1.1M | keeps a growing codebase from turning into mud |
| `vercel-labs/agent-browser` → **agent-browser** | 1.1M | lets an agent drive a browser — useful if you later let the agent gather evidence itself |
| `anthropics/skills` → **frontend-design** | 962K | so your web UI doesn't look like a prototype |
| `vercel-labs/agent-skills` → **vercel-react-best-practices**, **web-design-guidelines** | ~780K / 710K | frontend quality if you go React |
| `supabase/agent-skills` → **supabase-postgres-best-practices** | 435K | when you add a real database |
| `flowkit-labs/skills` → **reddit-automation** | 836K | if you want to gather real user complaints/pain points as evidence input |

Install set that pays off immediately for this project:

```bash
npx skills add vercel-labs/skills --skill find-skills
npx skills add https://github.com/juliusbrussee/caveman --skill caveman
npx skills add mattpocock/skills --skill tdd --skill diagnosing-bugs --skill code-review --skill domain-modeling --skill grill-me
npx skills add anthropics/skills --skill frontend-design
```

### 6d. Your own skills (already written for you)
Three skills in `skills/` in this repo, built with progressive disclosure (short body, detailed
references loaded only when needed):

| Skill | Purpose | References (lazy-loaded) |
|---|---|---|
| `culture-scout` | cultural fit analysis + the four hard entry checks (trust / payment rail / decision unit / legitimacy) | `culture-data-sources.md`, `entry-checks.md` |
| `case-file-analyst` | turn any article/filing/post-mortem into a schema-valid case record, with batch-mode coverage stats | `case-schema.md` |
| `idea-oracle-builder` | extend/debug/deploy this agent, swap the brain, cut tokens, avoid hallucinated sources | `free-stack.md`, `token-economy.md`, `sources-to-ingest.md` |

```bash
cp -r skills/* ~/.claude/skills/     # Claude Code
cp -r skills/* .cursor/skills/       # Cursor-style project skills
```

### 6e. Which agent to run the skills in
Free options, all supported by skills.sh: **Claude Code**, **Gemini CLI** (open-source, 100K ⭐),
**OpenCode**, **Goose**, **Cline** (VS Code), **GitHub Copilot**, **Windsurf**, **Zed**,
**Kiro CLI**, **Codex**. If you have no budget and want agentic coding free, **Gemini CLI** or
**OpenCode** with a free-tier key is the cheapest route.

---

## 7. Free hosting

| Platform | Best for | Catch (2026) |
|---|---|---|
| Cloudflare Pages / Vercel Hobby | static frontend | Vercel keeps only 3 recent prod deployments on Hobby; 10s serverless timeout |
| Hugging Face Spaces | Python/Docker backend, 2 vCPU / 16 GB on CPU Basic | public by default; sleeps on inactivity; some Space types moved behind a paid plan |
| Render | FastAPI/Flask backend | 512 MB, sleeps after 15 min, **free Postgres expires after 30 days** |
| Streamlit Community Cloud | Streamlit apps | ~1 GB RAM, ~12h idle sleep, US-only |
| Oracle Cloud Always Free | an always-on VM (best value if you tolerate ops) | Arm allowance was halved in 2026; you run it |
| GitHub Actions | **scheduled agent jobs** — build reports nightly, commit results | 2,000 free minutes/month on public repos |

**Best shape for this app:** it's stateless, so you don't need a database. Static frontend +
one backend endpoint (`/api/analyze`) + data in the repo. Keep API keys server-side only.

---

## 8. Architecture I built for you

```
                           ┌─────────────────────────────┐
   user's idea  ─────────▶ │  INTAKE (parse_idea)        │
   "coffee sub in         │  country · sector · budget  │
    Melbourne, $0"        │  · stage · mentioned places │
                           └──────────────┬──────────────┘
                                          ▼
   ┌────────────────────────────────────────────────────────────┐
   │ RETRIEVE  (retrievers.py)                                  │
   │  · culture profile   ← data/cultures.csv        (19 markets)│
   │  · case files        ← data/case_studies.json   (45 records)│
   │  · model patterns    ← data/patterns.json       (14 patterns)│
   │  TF-IDF + query expansion + tag boost + region affinity     │
   └──────────────┬─────────────────────────────────────────────┘
                  ▼
   ┌──────────────────────────────────────────┐
   │ PACK (pack_to_text)                      │
   │ cited evidence block, capped at 9k chars │  ← token budget enforced here
   └──────────────┬───────────────────────────┘
                  ▼
   ┌──────────────────────────────────────────────────────────┐
   │ REASON                                                    │
   │  Brain available?  → LLM with citation mandate            │
   │  No key / offline? → rule-based synthesis (same evidence) │
   │  Both paths also get pre-computed RISK FLAGS               │
   └──────────────┬───────────────────────────────────────────┘
                  ▼
   ┌──────────────────────────────────────────────────────────┐
   │ REPORT  10 sections + code-generated source list          │
   │  reality check · cultural fit · what worked · what died   │
   │  · model fit · risk flags · adaptations · 7-day $0 plan   │
   │  · kill criteria · what to verify                         │
   └──────────────────────────────────────────────────────────┘
```

Design decisions worth copying (or arguing with):
1. **Offline path is first-class.** The app is fully useful with no key, no internet, no money. LLMs are an upgrade, never a dependency.
2. **The model never writes the source list.** It's generated in code from the retrieved ids, so citations can't be fabricated.
3. **Risk flags are computed, not generated.** Rules run before the LLM, so the sharpest warnings don't depend on a model remembering to mention them.
4. **Cultural factors are mechanisms, not traits.** The corpus schema forbids "X people value Y" and requires "Y structure made Z happen".
5. **Every report carries its own bias warning** — survivorship bias, averages-not-individuals, verify-before-spending. This is a trust feature, and it's also honest.

---

## 9. Reality check — the parts you must not skip

| Risk | Why it kills this kind of product | Mitigation baked in |
|---|---|---|
| **Survivorship bias** | Case literature mostly records winners; "what worked" is the least reliable data in the world | failure-heavy corpus, per-record confidence, explicit caveat in every report |
| **Cultural stereotyping** | Country averages → "those people are like that" is both wrong and offensive | schema forbids trait language; reports state averages-not-individuals |
| **Hindsight bias** | Post-mortems compress messy causality into tidy cause → effect | `confidence` per record + "verify against primary source" section |
| **Hallucinated advice** | The classic LLM-advisor failure — confident, generic, uncited | citation mandate + code-generated sources + whitelist |
| **Free-tier rug-pull** | Providers retire models and cut quotas without notice | 6 providers + offline fallback, one interface to swap |
| **Licence trap** | CC BY-NC datasets can't ship commercially | licence column documented per source from ingestion |
| **Averages hide everything** | Within-country variation (urban/rural, religion, generation) usually exceeds between-country variation | present dimensions as hypotheses; always ask "which segment, which city?" |

**The honest commercial read:** this is a good *product* and a weak *moat* if the only thing you do is
wrap an LLM. The moat is (a) the structured, cited, failure-weighted corpus, (b) the
culture-and-mechanism framing, and (c) the specificity of the 7-day tests. All three are things a
general chatbot will not do for you. Charge for saved projects/PDF exports later; give away the
analysis until 20 people use it weekly.

---

## 10. Your next 14 days (all $0)

| Day | Do this | Output |
|---|---|---|
| 1 | `python3 server.py`, run 10 ideas you already know well | a list of where the output is wrong |
| 2 | Add free Groq + Gemini keys; compare LLM vs offline reports | a decision on whether the LLM is worth it |
| 3–5 | Write 15 case files with the `case-file-analyst` skill (≥5 failures, ≥4 countries) | corpus at ~60 records |
| 6 | `python scripts/fetch_data.py --check` | outcome/region balance report |
| 7 | Get 3 real people to use it unaided | their unanswerable questions = your roadmap |
| 8–9 | Answer the top question by adding a data layer | one new retrievable source kind |
| 10 | Add "what would have to be true" + export to PDF/Markdown | something worth sending to a partner |
| 11–12 | Deploy: static frontend + HF Spaces backend, key server-side, rate limit | a public URL |
| 13 | Install the token skills (`caveman`, `find-skills`, `tdd`) and measure `/context` before/after | a cheaper dev loop |
| 14 | Pick the beachhead audience and rewrite the landing copy for them only | a product with a user |

---

## Appendix: source list for this report

Agent framework comparisons and star counts: ayautomate.com (Sept 2026), fungies.io (Sept 2026),
resources.rework.com, vdf.ai (Oct 2026), ai-haven.com (Aug 2026) · Free LLM tiers:
klymentiev.com (Sept 2026), costbench.com (Aug 2026), freeapihub.com, stationx.net (Oct 2026),
github.com/open-free-llm-api/awesome-freellm-apis (updated 2026-10-08) · Free hosting:
snapdeploy.dev (Sept 2026), niteagent.com, miget.com (Jul 2026) · Vector DBs: klymentiev.com,
mcp.directory (May 2026), kunalganglani.com (Sept 2026) · Skills standard and token economics:
skills.sh leaderboard, claudecoworkcourse.com (Sept 2026), aitoolsreview.co.uk (Oct 2026),
dev.to token-efficiency guide, quintonwall.com (Jun 2026), strapi.io (Jun 2026) · Datasets:
Kaggle dataset pages, geerthofstede.com, worldvaluessurvey.org, CB Insights, data.worldbank.org ·
Learning repos: github.com/NirDiamant (five repositories), microsoft/ai-agents-for-beginners.

*All links verified reachable on 8 October 2026. Free-tier terms change frequently — re-verify before you depend on any single provider.*
