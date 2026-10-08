# The $0 build plan — from nothing to Sarathi Labs in 4 weeks

*Product: **Arthabodh** · engine: **Shodh***

Assumes: no money, one person, a laptop, and evenings. Every step is free and every step
produces something you can show someone.

---

## Week 0 (today, ~30 minutes) — get it running

```bash
cd sarathi-labs
python3 server.py                  # opens on http://localhost:8000  (no installs needed)
python3 cli.py --demo              # see a full report in the terminal
python3 cli.py --providers         # see which free brains you could switch on
```

Then add one free key (Groq is the fastest to get):

```bash
cp .env.example .env
# put your key in .env, then:
export $(grep -v '^#' .env | xargs) && python3 cli.py --idea "your idea here"
```

**Done when:** you get a culture-aware report with cited case files.

---

## Week 1 — prove the idea is worth building

1. **Write 10 idea reports from your own head**, all for markets you know something about.
   Where does the output feel wrong, generic, or obviously made up? Write it down.
2. **Fix the corpus, not the prompt.** 90% of bad output is thin evidence. Add 10 case files
   using the `case-file-analyst` skill — make at least 4 of them failures.
3. **Get 5 real people to run their own idea through it.** Watch them use it. Do not help them.
   Note every question they ask that the tool does not answer.
4. **Pick one beachhead audience** from those 5 people: who found the output most useful?
   That is your user. Delete the rest.

**Done when:** you can name the person who wants this and the one question they asked that you could not answer.

---

## Week 2 — make it genuinely better than a chatbot

The only reason this tool deserves to exist is that it retrieves real evidence. So deepen the evidence:

1. **Cross-country corpus.** Add case files from at least 6 more countries, weighted to your beachhead region.
2. **Add a second data layer** relevant to your audience, e.g.:
   - sector cost benchmarks (what a delivery actually costs per drop in that city)
   - licence/registration requirements per country
   - local customer acquisition channels that actually exist
3. **Add the "what would have to be true" section.** For every recommendation, list the assumptions
   it rests on. This is the feature that makes people trust the tool.
4. **Add an export button** producing a one-page PDF/Markdown brief people can send to a partner or bank.

Free storage for user data if you need it: pick one — browser `localStorage` (zero backend),
Supabase free tier, or a JSON file on the server. Do not build auth yet.

**Done when:** someone says "this told me something I did not know" — unprompted.

---

## Week 3 — deploy for free

Recommended zero-cost shape (because this app has no state):

| Layer | Free option | Why |
|---|---|---|
| Frontend | Cloudflare Pages or Vercel Hobby | static, fast, generous free tier |
| Backend | Hugging Face Spaces (Docker) **or** Render free web service | runs Python; both sleep when idle |
| Brain | Groq / Gemini / OpenRouter free tier, Ollama fallback | `brain.py` already auto-selects |
| Data | in the repo | no database needed yet |
| Analytics | none, or a free Plausible/Umami self-host later | do not add tracking to a 5-user product |

Deployment notes:
- Never put an API key in frontend code. If the key is in the browser, it is public.
- Put the LLM call behind the backend endpoint (`/api/analyze`) exactly as this repo does.
- Free hosts sleep. Add a friendly "waking up, ~30s" state rather than letting it look broken.
- Set a per-IP rate limit before going public (a simple in-memory counter is enough at this scale).

**Done when:** a stranger with the URL can get a report without you doing anything.

---

## Week 4 — decide: grow it, or use it

**If it is a product:** the next real problems are (a) evidence quality at scale, (b) latency,
(c) paying for it. For (c): keep the free tiers for the free product, and charge only for the
things that cost you money (long reports, PDF export, saved projects). Do not add a paid tier
until at least 20 people use it weekly for free.

**If it is a personal tool:** stop building features. Instead, run every business decision you
make through it, and add a case file every time you learn something the corpus got wrong.
A private tool with 200 honest case files beats a public app with 40.

---

## Upgrade path (only when you actually hit the limits)

| Trigger | Upgrade | Cost |
|---|---|---|
| Corpus > 5,000 chunks | Chroma or pgvector + `sentence-transformers` (local embeddings) | $0 |
| Reports too slow | cache by `hash(brief + evidence_ids)`; batch retrieval | $0 |
| Free LLM limits hit | stack a 2nd provider (already supported); or run Ollama locally | $0 |
| Free hosting sleeps too much | Oracle Cloud Always Free VM, or a $5 VPS | $0–5/mo |
| You need real user accounts | Supabase free tier auth | $0 |
| You get paying users | move the brain to a paid tier of the same API (`brain.py` only needs a key change) | usage-based |

## Things that will go wrong (plan for them)
- **A free provider deprecates your model** (Groq retired Llama models in Aug 2026; GitHub Models shut down in July 2026). Keep 2 providers configured at all times; `PROVIDERS` in `brain.py` exists for this.
- **A dataset licence bites you.** CC BY-NC datasets cannot go into a commercial product. Track licences in `data/README.md` from day one.
- **The corpus becomes unbalanced.** An all-Silicon-Valley corpus produces all-Silicon-Valley advice. Run `python scripts/fetch_data.py --check` and watch the region and outcome distributions.
- **You over-claim.** The moment the tool sounds confident about the future, it stops being useful. Keep the caveats in the header — they are a feature, not a disclaimer.

## What success looks like at week 4
- 5 weekly users who are not you
- ≥ 60 case files, ≥ 6 countries, ≥ 1 failure per 2 successes
- a report that is faster and more specific than asking a general chatbot
- $0 spent
