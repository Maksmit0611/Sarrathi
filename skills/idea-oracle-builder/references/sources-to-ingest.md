# Where to get more culture + business-outcome data (free)

Load when the user asks to expand the knowledge base.

## Business outcomes — what worked / what failed
| Source | What it gives | Access |
|---|---|---|
| Startup failure post-mortem datasets (Kaggle, e.g. "Startup Failures" with 13 failure-cause flags; "Startup Success/Fail from Crunchbase") | structured causes of death: no budget, competition, poor market fit, platform dependency, regulatory pressure, overhype | free download, check each dataset licence (several are CC BY-NC) |
| Financial distress datasets (Kaggle, Altman/Ohlson-derived) | quantitative failure prediction features | free, anonymised |
| CB Insights public post-mortem compilations | narrative "why startups fail" taxonomies | free to read, cite the index |
| Company filings + investor-relations archives (SEC EDGAR, ASX, Companies House, ASIC) | primary evidence for outcomes | free, public domain-ish |
| Founder interviews and long-form company histories (Acquired, HBR, business-school case archives) | mechanisms and causal detail | mostly free to read |
| World Bank / IFC SME and entrepreneurship data | cross-country business conditions | free, CC BY 4.0 |
| National statistics offices (ABS for Australia, ONS for UK, BPS for Indonesia, etc.) | sector size, survival rates, household spending | free |

## Culture and values
| Source | Gives | Notes |
|---|---|---|
| Hofstede dimension data matrix | 6 dimensions, ~100 countries | free for research; contact for commercial use |
| World Values Survey | longitudinal raw survey microdata, 80+ countries | openly available |
| GLOBE study | 9 dimensions, 60+ societies | published scores only; raw data not public |
| Pew Research Global Attitudes | religion, family, gender, technology attitudes | free with citation |
| World Bank Worldwide Governance Indicators | institutional trust proxies | free, CC BY 4.0 |
| UNESCO / national cultural statistics | language, religion, education distribution | free |

## Ingestion rules
1. **Record the licence for every source** in `data/README.md` the moment you ingest it.
   A corpus you cannot legally redistribute is a corpus you cannot publish with.
2. **Never mix a paid/restricted source into the public corpus.** Keep it in a separate private folder.
3. **Compress, don't dump.** A 500-word post-mortem should become one schema-valid record with a
   citation. Retrieval quality collapses when full articles are chunked and embedded.
4. **Prefer primary sources.** Filings over press releases; court records over commentary;
   the company's own numbers over a journalist's summary.
5. **Balance the corpus:** for every 2 `worked` records, add at least 1 `failed`, and cover at least
   3 world regions. Unbalanced corpora make an agent that only knows Silicon Valley.
