# Data provenance, licences and primary sources

*Corpus for **Arthabodh** (Sarathi Labs), retrieved by the **Shodh** engine.*

Everything in this folder is a **demo subset** assembled from public information. Read the warnings.

---

## `cultures.csv` — 19 markets × 6 dimensions

| Field | Meaning |
|---|---|
| `pdi` | Power distance — how much hierarchy is expected and accepted |
| `idv` | Individualism vs collectivism — individual choice vs group/family decision |
| `mas` | Masculinity vs femininity — competition/status vs care/quality-of-life framing |
| `uai` | Uncertainty avoidance — how much novelty and ambiguity a market tolerates |
| `lto` | Long-term vs short-term orientation — patience vs immediate visible value |
| `ivr` | Indulgence vs restraint — aspiration and enjoyment vs duty and durability |

**These values are approximate reference figures for demonstration, not the official dataset.**
The canonical source is the Hofstede dimension data matrix:
<https://geerthofstede.com/research-and-vsm/dimension-data-matrix/>
Free for research use; commercial use requires contacting the authors. Download the official
`.csv`/`.xls` and replace this file before you publish anything based on it.

### Hard limitations — read before using
1. **Country-level averages are not individuals.** A score of 20 for individualism does not describe any person in that country.
2. **Sample bias:** the original data came from a single multinational's employees in the 1960s–70s, later supplemented. It describes a slice of formal-sector workers, not a whole society.
3. **Nations are not cultures.** Regional, ethnic, religious, urban/rural and generational variation is often larger than the between-country differences.
4. **Scores drift.** Values change over decades; a 2010-era score may not describe 2026.
5. **Use as a hypothesis generator, never as a predictor of an individual transaction.**

### Confirmatory sources
- **World Values Survey** (raw, longitudinal, openly available): <https://www.worldvaluessurvey.org>
- **GLOBE study** (9 dimensions; published scores are usable, raw data is not public)
- **World Bank Open Data** (infrastructure, finance, business conditions — CC BY 4.0): <https://data.worldbank.org>
- For Australian local detail: **ABS** (industry counts, household expenditure, business survival rates)

---

## `case_studies.json` — 45 structured post-mortems

Each record carries `outcome` (worked / failed / mixed), what worked, what did not, cultural
factors at mechanism level, a transferable lesson, tags, a `confidence` level and the source type.

**Compilation and phrasing are original (released CC BY 4.0). The underlying facts are public
information**, drawn from company disclosures, court records, regulatory filings and mainstream
reporting. Where a claim is contested or thinly sourced, the record is marked `confidence: low`
or `medium` — treat those as hypotheses.

### Please internalise this limitation
> **Survivorship bias is the default state of all business case literature.**
> For every documented success there are thousands of unrecorded, near-identical failures.
> A case file is a **prior to test**, never a prediction. The failure records are the valuable
> half of this dataset.

Additional caveats:
- Compressed post-mortems flatten messy causality into a paragraph. Real failures are over-determined.
- Hindsight bias: people write tidy stories after the outcome is known.
- Attribution to "culture" is easy to over-claim. Each cultural factor here is written as a *mechanism*, and mechanisms can be wrong.

---

## `patterns.json` — 14 business-model archetypes

Each pattern has where it worked, where it failed, the signals that you need it, the resource level
required, and one cheap first test. Same caveat: priors, not rules.

---

## Free datasets to expand this corpus

Always check the licence on the dataset page before redistributing.

| Dataset | Use |
|---|---|
| Kaggle — *Startup Failures* (814 companies, 13 binary failure-cause flags) | structured causes of death with lessons |
| Kaggle — *"Big Startup Success/Fail from Crunchbase"* | success/failure classification at scale |
| Kaggle — *Financial Distress* (Altman/Ohlson-derived) | quantitative failure features |
| CB Insights — public post-mortem index | narrative failure taxonomies |
| SEC EDGAR / ASX announcements / Companies House / ASIC | primary evidence for any outcome claim |
| World Bank Open Data | market conditions per country, CC BY 4.0 |
| World Values Survey | values and attitudes, multiple waves |
| National statistics offices (ABS, ONS, BPS, NBS Kenya, etc.) | sector size, survival rates, household spend |

### Ingestion rules
1. Record the licence in this file the moment you ingest a source.
2. Never mix a non-redistributable source into a public corpus — keep it in a separate private folder.
3. Compress each source into one schema-valid record with a citation; do not dump full articles into the corpus.
4. Keep the corpus balanced: at least 1 failure record for every 2 success records, and at least 3 world regions.

---

## Licence summary

| File | Licence |
|---|---|
| `case_studies.json`, `patterns.json` (compilation and phrasing) | CC BY 4.0 — reuse with credit (Sarathi Labs) |
| `cultures.csv` dimension values | Research use; commercial use requires permission from the Hofstede authors. **Replace with the official matrix before any commercial deployment.** |
| Code in this repo | Apache-2.0 (see `../LICENSE`) |
