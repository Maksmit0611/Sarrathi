# Brand architecture — Sarathi Labs

**Sarathi Labs** is the lab. **Arthabodh** is the product. **Shodh** is the engine.
**Arthashastra** is the lineage. Four names, four separate jobs, nothing overlapping.

---

## The stack

| Layer | Name | Devanagari | Root meaning | Where it appears |
|---|---|---|---|---|
| **Lab / company** | **Sarathi Labs** | सारथि | *charioteer* — the one who drives and counsels, who does not fight your war but steers through it | GitHub org, copyright, About page, email signatures, the `/api/health` response |
| **Product** | **Arthabodh** | अर्थबोध | *understanding of artha* — comprehension of wealth and of meaning. अर्थ = that which one strives for (wealth · purpose · meaning); बोध = awakening into knowing | The report the user receives, the web UI, the CLI, the docs, everything user-facing |
| **Engine** | **Shodh** | शोध | *search + refinement* — from √śudh, to purify. To clear away what is false; what remains is knowledge | The loading state, the retrieval pipeline, engineering docs, the "Shodh engine retrieved N case files" line in every report |
| **Lineage** | **Arthashastra** | अर्थशास्त्र | Kautilya's ancient treatise on trade, taxation, markets, risk and strategy | The narrative layer — About page, "why this exists", talks and pitches |

### The one-line pitch
> **Sarathi Labs** builds **Arthabodh** — a research agent that runs a **Shodh** over real case files,
> in the **Arthashastra** tradition of Kautilya.

### The user-facing pitch
> ***"Shodh your idea. Get your Arthabodh."***

---

## Why this naming holds together

**The three names tell one story in sequence, which is exactly the user's journey:**

1. **Shodh** — the user's idea is investigated and refined. Search first, before spending.
2. **Arthabodh** — the user receives understanding: what the idea means *and* what it will do to their money.
3. **Sarathi Labs** — the lab that built the thing does not claim to be the hero. It steers. That is the
   honest posture for an advisor: your business is yours; we hold the reins and read the road.

**The lineage is the fourth layer, and it is load-bearing.** Kautilya's *Arthashastra* discusses market
analysis, competitor assessment, pricing, risk and the ethics of profit — the exact subject matter of
this product, written over two thousand years ago. Using it as the narrative layer gives the product
depth that a generic "AI advisor" cannot claim — and it costs nothing, because narrative cannot be
trademarked away from you.

---

## Usage rules (read before writing any copy)

### Capitalisation
| Correct | Wrong |
|---|---|
| Sarathi Labs | Sarathi labs, Sarathilabs, Sārathi Labs |
| Arthabodh | ArthBodh, Arth Bodh, Artha Bodh, arthabodh |
| Shodh | Shod, Shodh., SHODH |
| Arthashastra | Arthashastra, Artha-shastra, Arthasastra *(common alternative — pick one and be consistent)* |

**One spelling each, forever.** Sanskrit words suffer fatal spelling drift in roman script. Arthabodh in
particular gets written four different ways in the wild, which splits search traffic four ways. Fix the
spelling now; register the variants as redirects later.

### When to use which name
| Situation | Use |
|---|---|
| Someone asks "what do you do?" | "I built Arthabodh — it tells you whether your business idea fits a culture and what happened to the people who tried it." |
| They ask who made it | "Sarathi Labs. Small lab." Then stop talking about yourself. |
| Explaining how it works | "It runs a Shodh — a search over structured case files — and builds you an Arthabodh." |
| Someone asks "why Sanskrit?" | Tell them the Manthan/Darpan/Kautilya story, then the Shodh–Arthabodh pairing. Do not lecture. |
| Pitching to a serious audience | Lead with the Arthashastra lineage — market analysis, risk, competitor assessment. It signals rigour, not decoration. |

### Do not
- **Don't transliterate loosely in marketing.** अर्थबोध and शोध appear once, correctly, near the logo. More than that reads as costume.
- **Don't invent Sanskrit phrases** and present them as classical. A motto may be formed — the grammar of **शोधात् बोधः** *śodhāt bodhaḥ* ("from research, understanding") is straightforward — but **have a Sanskritist verify it before printing**, and never present constructed Sanskrit as scripture. That is the one mistake that costs credibility with exactly the audience you are courting.
- **Don't translate the names into English as the primary brand.** "Mirror", "Understanding" — those are explanations, not names.
- **Don't let the lineage become the product.** Arthashastra is context; Arthabodh is the thing people pay attention to.

### Do
- **Use the verb.** *"Shodh your idea"* is the single best sentence in the brand. It makes the engine a user action.
- **Name the artefact.** The output is *"your Arthabodh"* — a document, not a chat log. That distinction is a product feature, so use it constantly.
- **Keep Sarathi Labs in the background.** The lab steers; the product is what people name. This is the opposite of founder-as-hero branding, and it fits both the meaning of the word and the honest posture of the product.

---

## Pronunciation guide (for non-Sanskrit speakers)

| Name | Say it | Common mistake |
|---|---|---|
| **Sarathi** | *SAH-rah-thee* (soft, breathy *th* as in *Thar*; not *th* as in *thin*) | "sa-RATH-eye" |
| **Arthabodh** | *AR-tha-bodh* (breathy *dh* at the end, almost *bode*) | "artha-BOD" |
| **Shodh** | *SHOHDH* (breathy *d*) | "shod" as in horseshoe, or "shode" |
| **Arthashastra** | *ar-tha-SHAAS-tra* | putting the stress on *artha* |

Accept that the aspiration will be lost in English — that is fine. Keep the *meaning* explainable in one sentence, which is what actually travels.

---

## Naming inside the codebase

The rename was done with one rule: **user-visible things changed; import paths did not.**

| Thing | Before | After | Why |
|---|---|---|---|
| Python package | `idea_oracle` | `idea_oracle` *(unchanged)* | changing import paths breaks every install, tutorial and bookmark for zero user benefit |
| Product class | `IdeaOracle` | `Arthabodh` **with `IdeaOracle` kept as an alias** | existing code and tests keep working |
| Report title | `# Idea Oracle report` | `# Arthabodh — <your idea>` | visible branding |
| Report footer | *(none)* | *"Arthabodh is a product of Sarathi Labs. Processing by the Shodh engine…"* | attribution travels with every exported report |
| UI spinner | "analysing…" | "Running shodh — searching case files, culture profiles and model patterns…" | makes the engine a user-visible process |
| UI button | "Analyse my idea" | "Shodh my idea → Arthabodh" | the brand's best sentence, in the most-clicked element |
| `/api/health` | `{ok, brain, cases}` | `+ {product, lab, engine, version}` | machines can discover the brand too |
| License header | "Idea Oracle contributors" | "Sarathi Labs contributors" | attribution |

```python
# both work, forever
from idea_oracle import IdeaOracle   # original name
from idea_oracle import Arthabodh    # product name (same object)
```

---

## Decision log

| Date | Decision | Reasoning |
|---|---|---|
| 2026-10-08 | Shortlist of 32 Sanskrit-rooted names compiled; top five proposed as Manthan, Darpan, Sarathi, Udyam, Kautilya | `docs/NAMING.md` — tested for pronounceability, meaning fit, trademark collision and scalability |
| 2026-10-08 | **Chosen: Sarathi Labs / Arthabodh / Shodh** | Sarathi is the honest advisory archetype (steers, does not fight your war); Arthabodh names the deliverable and carries the wealth-and-meaning double sense plus the four puruṣārthas framing; Shodh names the method and inherits India's research vocabulary |
| 2026-10-08 | Manthan and Kautilya retained as narrative assets, not names | Manthan's metaphor (nectar + poison from one churning) belongs in the pitch; Arthaśāstra's authority belongs in the "why this exists" story. Neither needs to be a trademark. |
| 2026-10-08 | Python package deliberately **not** renamed | see table above |

---

## Still to do before launch

- [ ] **Trademark search** for "Sarathi Labs" and "Arthabodh" — [ipindia.gov.in](https://ipindia.gov.in), plus USPTO/EUIPO if global. Sarathi is a common word (also means *driver* in everyday Hindi) and will have collisions; the compound "Arthabodh" is far more ownable.
- [ ] **Secure handles:** GitHub org `sarathi-labs`, the domains (`sarathilabs.com/.in`, `arthabodh.com/.in`, `shodh.ai` if affordable), X, LinkedIn.
- [ ] **Test pronunciation** on 5 non-Indian speakers; write down how they spell each name. If Arthabodh comes back three different ways, that is your cue to lead with **Shodh** as the verbal brand and keep Arthabodh for the written product.
- [ ] **Have a Sanskritist verify** शोधात् बोधः before printing it anywhere.
- [ ] **Check the Hindi/Marathi/Bengali colloquial sense** of each word with native speakers of your target market — not just Sanskritists.
