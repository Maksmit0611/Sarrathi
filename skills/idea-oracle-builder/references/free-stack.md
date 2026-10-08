# The $0 stack — Arthabodh / Sarathi Labs

*Verified October 2026 — free tiers change monthly, re-verify before relying on limits.*

## Free LLM "brains" (all OpenAI-compatible, no credit card for most)

| Provider | Model to use | Free limits | Card? | Signup |
|---|---|---|---|---|
| Groq | `openai/gpt-oss-120b` | ~30 req/min, generous daily tokens | No | console.groq.com/keys |
| Google Gemini | `gemini-2.5-flash` | free tier in AI Studio, ~1.5k req/day historically | No | aistudio.google.com/apikey |
| OpenRouter | any `:free` model | ~20 req/min, 50/day (1,000/day after a one-off $10) | No | openrouter.ai/keys |
| NVIDIA NIM | `meta/llama-3.3-70b-instruct` | free prototyping tier, 120+ models | No | build.nvidia.com |
| Mistral | `mistral-small-latest` | free experiment tier (phone verification) | No | console.mistral.ai |
| Ollama (local) | `llama3.1`, `qwen2.5` | unlimited, offline, needs your own RAM/GPU | No | ollama.com/download |

**Strategy: stack them.** Register 2–3 providers, put keys in `.env`, and let `brain.py` auto-select.
Free tiers change often (Groq retired Llama models in Aug 2026; Cerebras moved to a paid trial;
GitHub Models shut down in July 2026). Always re-check the provider's rate-limit page.
Free-tier models are for development and low-volume use. Do not build a paid product on a free tier
you do not control — keep the provider list swappable, which `brain.py` already is.

## Free hosting

| Platform | Best for | Catch |
|---|---|---|
| Hugging Face Spaces | Python/Gradio/Docker demos, 2 vCPU / 16GB on CPU Basic | public spaces; sleeps on inactivity; Gradio/Docker spaces moved behind a paid plan for some tiers |
| Streamlit Community Cloud | Streamlit apps from a GitHub repo | ~1 GB RAM, sleeps after ~12h idle, US-hosted |
| Render | FastAPI/Flask backends, free Postgres | 512 MB RAM, sleeps after 15 min, free Postgres expires after 30 days |
| Vercel Hobby | frontend/Next.js | 100 GB bandwidth, 10s serverless timeout, 3 recent prod deployments |
| Oracle Cloud Always Free | a real always-on VM (best value if you tolerate ops) | Arm allowance was halved in 2026; requires you to run it |
| GitHub Pages / Cloudflare Pages | static site frontend only | no backend |
| Railway / Zeabur / Back4App | container hosting after trial | no-card options remain but shrink yearly |

**Recommended pairing for zero cost:** static frontend on Cloudflare Pages or Vercel +
backend on Hugging Face Spaces (Docker) + data in the repo. If your app has no server state
(like Arthabodh), skip the backend entirely and run the agent client-side or in a
scheduled GitHub Action.

## Free vector databases / retrieval

| Option | Notes |
|---|---|
| TF-IDF in pure Python (this repo) | 0 deps, best choice under ~5,000 docs |
| Chroma | `pip install chromadb`, embedded, Apache-2.0, perfect for local prototypes |
| pgvector via Supabase/Neon free | Postgres + vectors on the free DB quota |
| Qdrant | single binary or Docker, Apache-2.0; hosted free tier ~1 GB |
| FAISS | Meta's library, fastest local ANN, no server |
| Embeddings: `sentence-transformers` (`all-MiniLM-L6-v2`) | runs on CPU, free, offline — no API calls |
| Embeddings: Gemini / OpenRouter embedding endpoints | free tier, but network-bound |

## Free data
See `sources-to-ingest.md`.

## Rule of the $0 stack
Every component must have a **second option you can switch to in under an hour**. Free tiers
die. An architecture that assumes one free provider is a paid product with a delayed invoice.
