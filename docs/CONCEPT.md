# The idea — what Arthabodh is and why it exists

## The one-sentence version

**People type in a business idea; Arthabodh tells them whether it fits their culture, what happened to
the people who already tried it, and what to test first — with every claim cited to a source, for $0.**

---

## The problem

Every day, someone with very little money decides whether to start something. A tiffin service in
Bengaluru. A laundry run in Mumbai. A bakery in Naples trying to sell biscuits in Germany. A VR arcade
in Riyadh. A savings app for farmers in Kenya.

They have three bad options:

| Option | Why it's bad |
|---|---|
| **Ask a general AI chatbot** | Confident, generic, uncited. It will happily invent a market size and never mention the eleven lookalikes that folded. |
| **Google it** | You get listicles from 2019, funded-company PR, and one blog post that's actually an ad. |
| **Pay a consultant** | $5,000 minimum, and they're not going to tell you about a failure in Jakarta either. |

Meanwhile, the actual evidence sits in plain sight — post-mortems, filings, court records, academic
studies, the pattern of *"this worked in Manila and died in Berlin"* — unstructured, unsorted, and
invisible to the person who needs it most.

**The gap is not intelligence. It is grounded, culture-aware evidence, delivered cheaply, before money is spent.**

---

## Who it's for

| User | What they need |
|---|---|
| **First-time founder with no capital** | A reality check that costs nothing and doesn't require an MBA to read |
| **Small business owner expanding** | Whether the playbook that worked at home works in a new country — and which half of it doesn't |
| **Diaspora entrepreneur** | The cultural specifics nobody writes down: how trust, payment and family decision-making actually work in the market they left |
| **Anyone with an idea and no money** | Permission to test small, plus a plan for the next seven days |

They are not in San Francisco. They are in Melbourne, Mumbai, Nairobi, Naples, Jakarta and Riyadh —
and almost every existing tool for them was written as though they were in California.

---

## What makes it different

### 1. It never answers from the model's memory
The LLM only ever reasons over retrieved, cited evidence. If the corpus is silent on something,
the honest answer is *"no evidence in corpus"* — not a plausible-sounding guess. This single design
rule is what separates an advisor from a confident random-text generator.

### 2. Culture is a first-class input, not a footnote
19 markets with power distance, individualism, uncertainty avoidance, long-term orientation,
indulgence and **payment rails**. The report tells you whether novelty will be trusted (and if not,
what to build instead), who actually makes the buying decision, and how money physically moves in
that market. This is the part global tools skip entirely.

### 3. The failure column comes first
For every two successes in the corpus there is at least one failure. Nobody writes about failures,
which is exactly why they're the most valuable half: **failures are where the money is saved.**
Every report shows what killed the lookalikes before it shows what worked.

### 4. They get an artefact, not a chat log
The output is **your Arthabodh** — a document with a cultural fit read, cited case files, computed
risk flags, three market adaptations, a 7-day $0 validation plan, and kill criteria. Something you can
send to a partner, a bank, or your own family. Not a conversation you have to re-read.

### 5. It runs on $0
Python's standard library. No `pip install`, no API key, no build step, no server bill. Add a free
Groq or Gemini key and the prose gets better — the *evidence is identical either way*. People with
no money should not need money to research their idea.

### 6. It refuses to flatter
Every report must state the strongest argument against the idea. A tool that only agrees with you
is a mirror with the lights off.

---

## What it explicitly is NOT

| Not | Why that matters |
|---|---|
| **A success predictor** | Nobody can predict a business. Claiming it would be dishonest and would make the tool useless the first time it's wrong. |
| **A business plan generator** | Plans are fiction until tested. This gives you tests. |
| **Legal, tax or financial advice** | It tells you to verify licences and obligations in your jurisdiction, and points you at the primary source. |
| **A substitute for talking to customers** | It tells you *which* five people to talk to this week, and what to ask. |
| **Culturally authoritative** | Country-level averages are hypotheses, not people. Every report says so. |

---

## Where the value actually is (the honest commercial read)

Wrapping an LLM is not a moat — anyone can do it in an afternoon. Three things here are not:

1. **A structured, cited, failure-weighted, multi-region corpus.** Every record carries an outcome, a causal claim, a cultural mechanism, a lesson, a confidence level and a source type. That is slow, unglamorous work, and it compounds.
2. **The culture-and-mechanism framing.** Not *"Chinese people value relationships"* (a stereotype) but *"low institutional trust made escrow and in-product negotiation essential, so the platform that shipped them won."* A mechanism can be tested. A stereotype cannot.
3. **Specificity of the output.** Named cases, real numbers, a seven-day plan with pass conditions, and kill criteria. General chatbots produce none of these because they are not built to.

The corpus and the discipline are the product. The model is a commodity you can swap in an afternoon —
which is exactly why `brain.py` lets you.

---

## The honest limitations (stated up front, in every report)

- **Survivorship bias is the default state of business writing.** For every documented success there are thousands of unrecorded failures. Case files are priors to test, never predictions.
- **Country-level cultural scores are averages, not individuals.** Nations are not cultures; urban/rural, religious and generational variation is often larger than the between-country differences.
- **Hindsight bias flattens causality.** Post-mortems make messy failures sound tidy, and winners write their own history.
- **The demo corpus is small** — 47 case files, 19 markets. The pipeline is the product; the data is the work.
- **Free infrastructure changes.** Providers retire models and cut quotas without notice. Keep two configured; the offline path always works.

Stating these is not hedging. It is the difference between a tool people trust and a tool that
eventually embarrasses them.

---

## Where it's going

The 4-week, $0 plan is in [`ROADMAP.md`](ROADMAP.md). In short:

| Week | Goal |
|---|---|
| **0** | It runs today: `python3 server.py` |
| **1** | 10 more case files from markets you actually know; get 3 real people to use it unaided |
| **2** | Deepen the evidence — add cost benchmarks, licence requirements, real distribution channels per market |
| **3** | Deploy free (static frontend + Hugging Face Spaces or Render backend) |
| **4** | Decide: grow it as a product, or keep it as your private tool with 200 honest case files |

**The metric that matters isn't users. It's whether someone says "this told me something I didn't know" — unprompted.**

---

## Why the names

| Layer | Name | Meaning |
|---|---|---|
| Lab | **Sarathi Labs** | सारथि — *charioteer*. Krishna did not fight Arjuna's war; he held the reins and gave counsel at the moment of decision. |
| Product | **Arthabodh** | अर्थबोध — *understanding of artha*: of wealth **and** of meaning. अर्थ is one of the four puruṣārthas — prosperity pursued as a legitimate aim, not greed. |
| Engine | **Shodh** | शोध — *search + refinement*, from √śudh, *to purify*. Clear away what is false; what remains is knowledge. |
| Lineage | **Arthashastra** | Kautilya's treatise on trade, markets, risk and strategy — this product's subject matter, written 2,300 years ago. |

Full reasoning, pronunciation and usage rules: [`BRAND.md`](BRAND.md).
The research behind the name (32 Sanskrit-rooted candidates): [`NAMING.md`](NAMING.md).
