---
name: case-file-analyst
description: Turn a business post-mortem, article, annual report or interview into a structured case file with what worked, what failed, the cultural factors and a transferable lesson. Use when the user shares a company story, asks "why did X fail", "what can I learn from X", wants to add evidence to a business knowledge base, or is building datasets of business outcomes. Produces records matching the Arthabodh (Sarathi Labs) case_studies.json schema.
---

# Case File Analyst

Convert messy narrative about a company into one structured record that another agent can retrieve and cite.

**Why the structure matters:** a story is not usable as evidence. A record with an outcome, a causal claim,
a confidence level and a source is. This skill exists to make the difference.

## Workflow

### 1. Identify the unit
Name, country, region, era (start–end), sector, business model. If the "company" is actually several
(e.g. a market comparison), split into separate records — one per entity.

### 2. Find the outcome and prove it is an outcome
Choose exactly one: `worked` / `failed` / `mixed`.
- `worked` requires evidence of survival or profit at scale over time — not funding raised, not press coverage.
- `failed` requires shutdown, bankruptcy, exit, or a documented collapse of the core business.
- `mixed` when it worked in one market/era and failed in another. Say which is which.

**Trap:** funded ≠ successful. Acquired ≠ successful. Viral ≠ successful. If the record only shows
fundraising or attention, mark the outcome `unknown` and say what evidence is missing.

### 3. Separate what worked from what did not
Both fields are mandatory and both must be causal, not descriptive.
- Bad: "It grew fast."
- Good: "Free listings removed the fee barrier while Alipay escrow solved the stranger-trust problem, so volume grew without ad spend."

### 4. Extract cultural factors
Only include a cultural factor if it changed an outcome. Format: `mechanism`, not `trait`.
- Bad: "Chinese people value relationships."
- Good: "Low institutional trust made escrow and in-product negotiation essential, so the platform that shipped them beat the one that did not."

Never write about a nationality's character. Write about institutions, norms, transaction structures and constraints.

### 5. Write the key lesson as a transferable rule
One sentence, usable as a prior by someone in a different sector. If it only applies to that company,
it is not a lesson — it is trivia. Keep it.

### 6. Set confidence honestly
| Level | Means |
|---|---|
| `high` | documented in filings, court records, or multiple independent major outlets |
| `medium` | partially documented, contested, or reconstructed from secondary sources |
| `low` | widely repeated, weakly sourced, or a common narrative with no primary evidence |

When in doubt, go one level lower. A knowledge base with false `high` labels is worse than a small one.

### 7. Emit the record
Output JSON that validates against `references/case-schema.md`. Append to `data/case_studies.json`
under `cases` if the user is building the Arthabodh corpus.

## Batch mode
When processing many records, also report:
| Metric | Value |
|---|---|
| records processed | n |
| outcome distribution | worked x / failed y / mixed z |
| confidence distribution | high / medium / low counts |
| geographic distribution | counts per region |
| sector coverage gaps | sectors with < 3 records |

A corpus of 40 US tech successes teaches you nothing about Indonesia. The coverage table is the point of batch mode.

## Guardrails
- **Survivorship bias is the default state of business writing.** State it in every batch summary.
- Never invent numbers. If revenue or date is unknown, write `unknown`. `unknown` is a valid value; a guess is not.
- Do not launder a press release into a case study. If the only source is the company, say so.
- Refuse to add a record whose "lesson" is a stereotype about a population.

## References (load only when needed)
- `references/case-schema.md` — exact JSON schema, field rules and worked examples
