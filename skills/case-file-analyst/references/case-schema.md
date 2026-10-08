# Case file schema (v1)

Load only when writing records into the knowledge base.

```json
{
  "id": "kebab-case-name-and-years",
  "name": "Company or case name",
  "region": "North America | Latin America | Europe | Middle East | Africa | Asia | Oceania | Global",
  "country": "Primary country",
  "era": "1975-2012 | 2007-present",
  "sector": "lower case sector string",
  "model": "business model in plain words",
  "outcome": "worked | failed | mixed",
  "what_worked": "causal sentence, 1-2 max",
  "what_didnt": "causal sentence, 1-2 max",
  "cultural_factors": ["mechanism-level statements only"],
  "key_lesson": "one transferable sentence",
  "tags": ["lowercase-hyphenated", "3-6 tags"],
  "confidence": "high | medium | low",
  "source_type": "where the record came from, e.g. 'SEC filings + 2 independent outlets'"
}
```

## Field rules
| Field | Rule |
|---|---|
| `id` | unique, lowercase, hyphenated, ends with the era. Never reuse an id. |
| `outcome` | exactly one of the three values. No "unknown" in the corpus — put uncertain ones aside instead. |
| `what_worked` / `what_didnt` | both required, even for `worked`/`failed` records. A success that did nothing wrong is a mislabelled record. |
| `cultural_factors` | 1–3 items. Mechanism, not trait. If none genuinely mattered, use an empty list rather than inventing. |
| `tags` | reuse existing tags where possible so retrieval clusters. Common tags: `market-entry`, `localisation`, `trust`, `unit-economics`, `hype`, `governance`, `network-effects`, `distribution`, `regulatory-risk`. |
| `confidence` | err downward. Choose the level the *weakest* key claim supports. |

## Worked example (good)
```json
{
  "id": "jollibee-vs-mcdonalds-philippines",
  "name": "Jollibee vs McDonald's in the Philippines",
  "region": "Asia",
  "country": "Philippines",
  "era": "1981-present",
  "sector": "Quick-service restaurants",
  "model": "Franchise / company-owned QSR",
  "outcome": "worked",
  "what_worked": "Matched Filipino taste (sweet spaghetti, rice meals, Chickenjoy) instead of selling the American menu, and built store density in the 1980s before McDonald's localised.",
  "what_didnt": "Overseas expansion struggled wherever its Filipino flavour profile had no diaspora customer base.",
  "cultural_factors": [
    "Rice-and-sweet flavour profile is core to local food identity, so a US menu could not substitute for it",
    "Family and celebration dining norms rewarded a brand built around sharing"
  ],
  "key_lesson": "A local champion that owns the local taste, price point and store density can beat a global giant that assumes its menu travels.",
  "tags": ["localisation", "local-champion", "food-and-beverage", "density"],
  "confidence": "high",
  "source_type": "Company disclosures + market share reporting"
}
```

## Worked example (bad — do not write this)
```json
{
  "name": "A startup that failed",
  "outcome": "failed",
  "what_didnt": "They ran out of money and the founders were not committed enough.",
  "cultural_factors": ["The culture was risk-averse"],
  "key_lesson": "You need passion to succeed.",
  "confidence": "high"
}
```
Why it is bad: no id, no era, no source; "ran out of money" is a symptom not a cause; "the culture was
risk-averse" is a stereotype with no mechanism; "passion" is not transferable; confidence is unjustified.

## Corpus health checks (run after batch edits)
```bash
python3 - <<'PY'
import json, collections
c = json.load(open("data/case_studies.json"))["cases"]
print("cases:", len(c))
print("outcomes:", collections.Counter(x["outcome"] for x in c))
print("confidence:", collections.Counter(x["confidence"] for x in c))
print("regions:", collections.Counter(x["region"] for x in c))
print("missing fields:", [x.get("id") for x in c if not all(k in x for k in
      ("id","outcome","what_worked","what_didnt","cultural_factors","key_lesson","confidence","source_type"))])
PY
```
Target benchmark for a usable corpus: **≥ 30 records, ≥ 3 regions, every outcome present, ≥ 1 `failed` record for every 2 `worked` records** (failure-heavy is a feature — it is where the savings are).
