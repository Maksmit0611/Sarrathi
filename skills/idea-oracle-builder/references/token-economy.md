# Token economy: how skills make agents cheaper

## The three-tier loading model (progressive disclosure)
| Tier | What loads | When | Cost |
|---|---|---|---|
| 1 | skill name + description only | always, at startup | ~30–100 tokens per skill |
| 2 | full `SKILL.md` body | only when the skill is triggered | typically 1–5k tokens |
| 3 | `references/*`, `scripts/*` | only when a step needs them | effectively unlimited, and **scripts cost nothing**: only their output enters context, never their source |

This is why you can install 50 skills and still have a lean context window. It is also why the
rule for writing skills is: **the body is the workflow, the references are the detail.**

## Practical rules
1. Keep `SKILL.md` under ~500 lines / ~6 KB. If it is bigger, move the bulk to `references/`.
2. Keep the `description` to 1–2 sentences — it loads every single session for every user.
   It must contain trigger keywords, because it is the only thing the agent uses to decide.
3. Put rare branches in reference files and point at them explicitly ("load `references/x.md` only when...").
4. Replace prose instructions with **scripts**. A validation script's code never enters the
   context window — only its output does. This is the single biggest token saving available.
5. Never paste large data into a skill. Reference the file path and let the agent read it.

## Measured effects (reported by practitioners, 2026)
- Splitting a fat `SKILL.md` into body + references: **~60% fewer tokens per trigger** on the big skills.
- One documented case: session cost $3.60 -> $2.64, wall time 17m -> 9m, new tokens 361k -> 169k, cache efficiency 15:1 -> 40:1.
- Terse output styles (e.g. the `caveman` skill) report **~75% fewer output tokens** while preserving
  technical accuracy — but always disable compression for security warnings and irreversible actions.

## Applying it to this project
- `MAX_EVIDENCE_CHARS = 9000` in `agent.py` caps the evidence block regardless of corpus size.
- The rule-based path costs **zero** tokens and runs before any LLM call.
- Sources are generated in code, not by the model — the model never spends tokens listing them.
- Cache key suggestion: `sha1(brief_text + sorted(evidence_ids))` -> skip the LLM entirely on repeat queries.

## How to measure your own
- Claude Code: run `/context` before and after a change.
- Any provider: log `usage.prompt_tokens` and `usage.completion_tokens` per request; store them in a CSV; watch the trend, not the snapshot.
- Track **tokens per report**, not tokens per call — the agent that makes 3 cheap calls can beat the one that makes 1 expensive call.
