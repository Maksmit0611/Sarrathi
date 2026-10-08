# GitHub listing copy — copy-paste ready

Everything below is written to fit GitHub's actual fields and limits. Nothing needs editing.

---

## 1. The repository description (the "About" field)

**Field limit: 350 characters.** This text appears in GitHub search results, on your profile, and in
the social preview card when someone shares the link. Keep it under ~160 characters so it never gets
truncated anywhere.

### ⭐ Recommended — paste this one

```
Culture-aware business idea validator. Runs a Shodh over 47 real case files to produce your Arthabodh — cited, honest, $0 to run, zero dependencies.
```
*155 characters. Names the product, the engine, the benefit, and the two facts that make people click: free, and no install.*

---

### Alternatives, depending on what you want to lead with

**If you want the cultural angle first:**
```
Test a business idea against 19 cultures and 47 real post-mortems. Free, dependency-free, every claim cited to a source.
```
*116 characters.*

**If you want the developer/hacker angle first:**
```
Grounding-first research agent. No dependencies, no API key needed, offline fallback. Runs a Shodh over case files and returns cited evidence, never vibes.
```
*155 characters.*

**If you want it maximally plain and clear:**
```
Paste in a business idea. Get back what worked, what failed, and what to test first — across 19 cultures. Runs at $0 with Python's standard library.
```
*143 characters.*

**If you want curiosity (good for Hacker News / Reddit launches):**
```
An agent that tells you what killed the businesses that looked like your idea. 47 case files, 19 cultures, zero dependencies, $0 to run.
```
*130 characters.*

---

## 2. The website field

Use it for whichever you have. If you have nothing deployed yet, point it at the roadmap so visitors
know the project is active:

```
https://github.com/YOURNAME/sarathi-labs/blob/main/docs/ROADMAP.md
```

Once deployed, swap in the live URL.

---

## 3. Repository topics (the tags)

GitHub allows **up to 20**. Paste these into the *Topics* field — they decide whether anyone ever
finds the repo through search:

```
ai-agents
rag
llm
python
business-research
agent-skills
startup-validation
cultural-intelligence
retrieval-augmented-generation
zero-cost
no-dependencies
market-research
groq
ollama
prompt-engineering
knowledge-base
case-studies
sanskrit
data-engineering
hacktoberfest
```

**Priority order if you only add a few:** `ai-agents`, `rag`, `llm`, `python`, `business-research`,
`agent-skills`, `zero-cost`.

---

## 4. Social preview / link-preview blurb

Used when the link is shared on X, LinkedIn, Slack or WhatsApp. Make the *first sentence* carry the
whole pitch, because that's all most people read.

> **Arthabodh by Sarathi Labs** — a business-idea validator that tells you what happened to the
> people who already tried your idea.
>
> You type in an idea. It runs a **Shodh** over 47 structured case files and 19 cultural profiles,
> then hands you back your **Arthabodh**: the cases that worked, the cases that died, the risk flags,
> and a 7-day test plan that costs nothing.
>
> Every claim is cited to a source. The LLM never answers from memory — it only reasons over
> retrieved evidence, which is what stops it inventing confident nonsense.
>
> Runs on Python's standard library. No `pip install`, no API key, no build step. Add a free Groq or
> Gemini key to switch on nicer prose; leave it off and it still works.

---

## 5. The pinned-release description

If you cut a `v0.2.0` release, use this:

```
v0.2.0 — "Arthabodh"

First branded release. Sarathi Labs ships Arthabodh, powered by the Shodh engine.

- 47 case files, 19 markets, 14 business-model patterns
- Citation discipline: sources are generated in code, never by the model
- 6 free LLM providers + offline rule-based fallback (works with no API key)
- Web UI, CLI and JSON API on the Python standard library alone
- 63 regression tests, CI on every push
```

---

## 6. What NOT to write

| Avoid | Why |
|---|---|
| "An AI-powered revolutionary platform..." | Every repo says this. It signals nothing and reads as marketing. |
| "Uses GPT-4 / Claude / [model name]" | Your design deliberately lets the model be swapped. Naming one dates the project and undersells the architecture. |
| "Predicts whether your startup will succeed" | **This is a false claim and it's the one that will get you attacked in comments.** You do not predict. You surface priors and tests — say that, because it's both true and more interesting. |
| "100% accurate" / "no hallucinations possible" | Unprovable. Say "every claim cites a source" instead — that's checkable. |
| Emoji-heavy descriptions | GitHub renders the About field as plain text; emoji eat your character budget and read as unserious in search results. |

---

## 7. Two fields people forget

**The README's first line matters more than the About field.** It's what a visitor reads after
clicking. Yours currently opens with the product name, which is right — keep the pitch within the
first two lines.

**Set the repo's social preview image** (Settings → Social preview). A single screenshot of a real
Arthabodh report roughly doubles click-through compared to the default placeholder. Use your own
data, not the demo, so it looks like a working product rather than an example.
