# Culture data sources (free, for the culture-scout skill)

Load this file ONLY when the target country is missing from `data/cultures.csv`.

## 1. Hofstede dimension data matrix — primary source
- URL: https://geerthofstede.com/research-and-vsm/dimension-data-matrix/
- Gives: PDI, IDV, MAS, UAI, LTO, IVR for ~100 countries. `.csv`, `.xls`, `.sav` downloads.
- Licence: free for research use without permission. **Commercial use requires contacting the authors.**
- Use for: the six dimension scores. This is the canonical version — prefer it over any third-party copy.

## 2. World Values Survey (WVS) — raw, longitudinal, openly licensed
- URL: https://www.worldvaluessurvey.org/WVSContents.jsp
- Gives: raw survey microdata, multiple waves since 1981, 80+ countries. You can compute your own indices.
- Licence: openly available to researchers; check current terms per wave.
- Use for: questions Hofstede does not ask — religiosity, gender norms, trust in institutions, attitudes to work and family.

## 3. GLOBE study
- Gives: 9 dimensions × 2 ("as is" vs "should be"), 60+ societies.
- Access: book/paid data — underlying individual-level data is **not** public. Use published country scores in academic papers; cite them; do not redistribute the raw data.

## 4. World Bank Open Data / Doing Business alternatives
- URL: https://data.worldbank.org
- Gives: ease of starting a business, financing, logistics, electricity reliability, internet penetration.
- Licence: CC BY 4.0 for most datasets.
- Use for: the "payment rail" and "licence" checks — infrastructure facts, not opinions.

## Method rule
Never mix sources in one score table without labelling. If Hofstede and GLOBE disagree (they often do), present both and say they measure different things. Do not average them.
