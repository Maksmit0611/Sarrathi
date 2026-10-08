# How to build an agent (not an app)

*Research note, Sarathi Labs · 2026-10-08 · sources at the bottom.*

You asked for the information on building an **agent** rather than an app. This is that
document: what the difference actually is, the architecture, the decisions that matter,
and what it costs. Every claim here is reflected in code that runs in this repo — the
chapter headings map to real files, so you can read the theory and the implementation
side by side.

---

## 1. The difference, stated precisely

| | App | Agent |
|---|---|---|
| Trigger | someone visits it | it runs, or you call it |
| State | request → response, forgotten | remembers you across sessions |
| Output | a screen | a file, an action, a changed system |
| Control flow | you wrote every branch | the model chooses the next step |
| Failure | error page | retries, degrades, tells you what it did |

An app is a place you go. An agent is a thing that goes. That single sentence is the
whole reframe.

Practically, four properties make something an agent:

1. **A loop** — it keeps acting until the goal is met, not until one response is produced.
2. **Tools** — it can affect the world (files, shell, web, APIs), not just talk about it.
3. **Memory** — what it learns in session 1 is available in session 9.
4. **Autonomy** — it can run when you are asleep (a schedule, a queue, a trigger).

Miss any of those and you have a chatbot with a plugin. All four, and it is an agent.

---

## 2. The loop (the 60 lines that matter)

Everything else is detail. The core is:

```
messages = [system prompt]
messages.append(user goal)

for step in range(max_steps):
    reply = model.chat(messages, tools=tool_schemas)
    if reply has no tool_calls:
        return reply.content                  # done
    messages.append(reply)                    # the model's request to act
    for call in reply.tool_calls:
        result = run_the_tool(call.name, call.arguments)
        messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
```

Three things people get wrong here:

- **No step budget.** A model that keeps calling tools will loop forever, costing money
  and time. Cap it (`max_steps`, usually 5–10) and *report* that you hit the cap rather
  than pretending the task finished.
- **Swallowing tool errors.** A tool that raises must return an error *string* to the
  model, not crash the loop. The model can often recover; a traceback cannot.
- **Truncating the wrong thing.** Tool output is where the tokens go. Cap each result
  (we use 6,000 chars per call, 2,000 stored) — not the conversation history.

*Implemented in:* `sarrathi/loop.py`. *Verified by:* `tests/test_agent.py::test_llm_loop`
(mock brain proves tool call → result → answer, without an API key).

---

## 3. Tool calling, and how to write tools that don't break

A tool is three things: a **name**, a **JSON Schema** of its arguments, and a **Python
function**. The first two are the model's entire world; the third is yours.

```python
REGISTRY["remember"] = Tool(
    name="remember",
    description="Store something durable about the user. Not for small talk.",
    parameters={"type": "object",
                "properties": {"text": {"type": "string"},
                               "kind": {"type": "string", "enum": ["fact", "decision", "preference"]}},
                "required": ["text", "kind"]},
    fn=remember_fn,
)
```

Hard-won rules:

- **Descriptions are prompts.** "Search memory" gets called wrongly; "Call this before
  asking the user for something they may have told you before" gets called correctly.
  Write the trigger condition, not the mechanic.
- **Every tool costs tokens forever.** All schemas ride along in every request of every
  session. Roughly 150–250 tokens per tool: twenty tools is ~4,000 tokens *before the
  user types anything*. Keep the surface small; move rare abilities behind a skill or an
  MCP server you connect on demand.
- **Validate, then execute.** Models hallucinate argument shapes — wrong key names,
  strings where integers go, extra fields. Catch `TypeError`, return a readable error,
  and the model usually fixes itself on the next step.
- **Return text, not exceptions.** `"error: file does not exist: /x"` is a result the
  model can act on. An exception is a dead turn.
- **Beware tools that return everything.** Any list-returning tool needs `limit`,
  `offset` or `orderBy`, or one call will flush your context window.
- **Raising beats lying.** A tool that fails silently and returns a success-shaped body
  teaches the agent a false world. Fail loudly in the tool; let the loop decide.

*Implemented in:* `sarrathi/tools.py` (13 tools, each with a `danger` rating).
*Verified by:* `test_tools` (bad args, missing files, deny-listed shell, bad schemes).

---

## 4. Memory: three tiers, cheapest first

The naive approach — "the messages array is the memory" — is right for one session and
useless across a week. The ladder:

| Tier | What it is | Cost | Fails when |
|---|---|---|---|
| 1. Session buffer | recent turns in the prompt | free | context fills (~20–50 turns) |
| 2. Summarised store | the model writes durable facts to disk | one extra tool call | the model forgets to write, or writes junk |
| 3. Semantic recall | search over the store, inject top-k | index + query | scale, or synonyms it can't see |

Two implementation notes that matter more than the choice of store:

- **Append-only JSONL beats a database at this scale.** One JSON object per line, one
  fact per line: never corrupts, greps with `grep`, diffs in git, readable by a human at
  2am. Vector databases earn their keep past a few thousand facts, not at fifty.
- **Lexical search beats embeddings for facts.** TF-IDF over a few hundred memories
  returns the right thing, costs nothing, runs offline, needs no GPU and no API key.
  Embeddings win on fuzzy, conceptual recall — a different problem.
- **Keep a human-readable digest.** Ours regenerates `MEMORY.md` on every write. If you
  cannot read what your agent believes about you, you cannot debug it — and "cheap
  models poison memory" is a real, observed failure mode in the wild. Let strong models
  write; let any model read.

*Implemented in:* `sarrathi/memory.py` (tier 2 + 3), reusing the Shodh engine's TF-IDF
index. *Verified by:* `test_memory` (dedupe, reload, recall, digest).

---

## 5. Identity: put the personality in files, not in code

A prompt buried in source is unreviewable and un-editable. The convention that works —
used by self-hosted agents like OpenClaw — is three small markdown files:

- `IDENTITY.md` — name, role, vibe.
- `SOUL.md` — behavioural rules. **This is the file that changes behaviour.** Ours
  includes "name the strongest argument against the user's idea; flattery is failure."
- `USER.md` — who the human is, written by the agent as it learns.

The payoff: you tune your agent by editing a text file, you can version it in git, and
identity is portable between frameworks. Separating *identity* from *instructions*
("how to call tools") also keeps prompts shorter and easier to reason about.

*Implemented in:* `sarrathi/identity.py`. *Verified by:* `test_identity` (edit
`USER.md` → it reaches the system prompt of the next session).

---

## 6. Brains: providers, and the $0 requirement

Any OpenAI-compatible endpoint gives you tool calling. The variable is the base URL and
the model name, nothing else:

| Provider | Free tier | Tool calling | Note |
|---|---|---|---|
| Groq | yes, no card | yes | fastest free tier; `gpt-oss-120b`, Llama models |
| Google Gemini | yes | yes | `gemini-2.5-flash`, generous limits |
| OpenRouter | `:free` models | yes | one key, many models; keep the pool to strong ones |
| NVIDIA NIM | yes | yes | credits on signup |
| Mistral | yes | yes | free experimental tier |
| Ollama (local) | free forever | yes | `base_url=http://localhost:11434/v1`, `api_key="ollama"` |
| **No model at all** | free | n/a | rule-routed tools: research, memory, files still work |

The last row is the one people skip, and it is why our agent is never useless: with no
key, no network and no money, it still researches, remembers, writes reports and
answers questions about what it knows. The model *upgrades* it; it does not enable it.

Honest limits of small local models: past a few steps they lose the thread, they
hallucinate tool arguments, and they call the same tool twice. Scope tasks narrowly,
validate every input, and never let a 3B model near your shell.

*Implemented in:* `idea_oracle/brain.py::chat_tools` + `sarrathi/loop.py::_offline_turn`.

---

## 7. MCP: how your agent gets new abilities without new code

The Model Context Protocol ("USB-C for AI tools", open-sourced by Anthropic in late 2024)
is the standard interface between agents and capabilities, with 12,000+ public servers.

```
agent  ──MCP client──►  MCP server  ──►  filesystem / GitHub / Postgres / browser / ...
```

Four things worth knowing before you write one:

- **Transport:** `stdio` for local servers (what nearly everyone uses), HTTP/SSE or
  streamable HTTP for remote. JSON-RPC 2.0 either way — you can hand-roll a client in
  ~120 lines of stdlib Python, which is what `sarrathi/mcp_bridge.py` does.
- **Three primitives:** *Tools* (the model invokes), *Resources* (the app fetches, with
  URI templates and cache hints), *Prompts* (parameterised templates). Tools get all the
  attention; resources are how you avoid stuffing context with things the model didn't
  need yet.
- **Design rules:** small tool surface, `limit`/`orderBy` on anything that lists, raise
  on failure rather than returning a success body, and scope filesystem roots at startup
  with normalised paths.
- **Security:** an MCP server is a program your agent can invoke thousands of times an
  hour. Rate-limit per token, per tool, per IP. Treat every server as untrusted code
  with your filesystem on the other side.

Under MCP, tools are namespaced (`mcp__<server>__<tool>`) so a remote tool can never
shadow a local one.

*Implemented in:* `sarrathi/mcp_bridge.py`. *Verified by:* `test_mcp` — a stub MCP server
is spawned over stdio, handshaken, listed, called, and its failure path exercised.

*If you prefer the official SDK:* `pip install "mcp[cli]"`, then
`from mcp.server.fastmcp import FastMCP` and decorate with `@mcp.tool()`. Modern
releases also expose `from mcp.server import MCPServer`. Your type hints become the JSON
Schema automatically.

---

## 8. Autonomy: running without you

This is where an app cannot follow. Three patterns, in increasing order of commitment:

1. **One-shot** — `python3 agent.py "research X"`. Good for scripting and pipes.
2. **Schedule** — a queue file plus cron:
   ```
   0 8 * * 1  cd ~/sarathi-labs && python3 agent.py --watch >> ~/.sarrathi/logs/cron.log 2>&1
   ```
   The agent wakes on Monday morning, works the queue, archives the run, goes back to
   sleep. You read the results with coffee.
3. **Service** — a long-running process (systemd unit, Docker container, VPS) with a TUI
   or a chat bridge (Telegram/Slack/WhatsApp), plus sub-agents for parallel work. This is
   the OpenClaw pattern: TUI + gateway, hooks for memory, workspace on disk, 2–4 GB RAM
   VPS, model server possibly on another machine on the LAN.

The rule that keeps this honest: **any scheduled agent must be able to explain what it
did.** Log every tool call with arguments and results (`Step` in `loop.py`), archive each
run to a file, and make the log human-readable.

---

## 9. Safety, honestly

An agent with tools is a small program with your permissions. The minimum viable guard
rails, all of which we implement:

- **Allow-list shell commands**, and keep a deny-list as a second net (`rm -rf`, `sudo`,
  `dd`, `mkfs`, fork bombs). Never pass user text straight to `shell=True`.
- **Scope the filesystem.** Resolve paths and check the prefix; a resolved-root check is
  what stops `../../etc/passwd`.
- **Confirm irreversible actions.** Deleting, sending, publishing, paying: ask first.
- **Cap the loop and cap the spend.** Step limits, and a provider key with a hard quota.
- **Log everything the agent did**, with the arguments it used. Silent autonomy is
  indistinguishable from a bug, until it isn't.

---

## 10. Do you need a framework?

| Approach | Use when | Cost |
|---|---|---|
| Plain Python (this repo) | you want control and auditability | ~400 lines you fully understand |
| `mcp[cli]` | you need an MCP server | one dependency |
| CrewAI | multi-agent role-play, fast prototypes | framework lock-in, opaque prompts |
| LangGraph | graph state, checkpoints, human-in-the-loop | steepest learning curve, worth it at real scale |
| n8n | you want no code | hosting, and JSON instead of Python |
| Goose / Letta / Agent Zero / OpenCode | you want a finished agent now | their opinions, not yours |

Frameworks earn their keep at multi-agent orchestration and durable workflows. Below
that, a loop, a tool registry and an append-only memory file are easier to debug than any
graph library — and you will need to debug.

---

## 11. What we actually built

| Chapter | File | Lines |
|---|---|---|
| The loop | `sarrathi/loop.py` | 363 |
| Tools | `sarrathi/tools.py` | 368 |
| Memory | `sarrathi/memory.py` | 249 |
| Identity | `sarrathi/identity.py` | 97 |
| MCP client | `sarrathi/mcp_bridge.py` | 208 |
| Entry point | `agent.py` | 236 |
| Tests | `tests/test_agent.py` | 362 (72 checks) |

Standard library only. No framework, no database, no API key required, total cost $0.
Run it: `python3 agent.py` (see `docs/AGENT.md`).

---

## Sources

- Anthropic — *Introducing the Model Context Protocol* (Nov 2024) and the MCP spec +
  transport docs (rev. 2025-06-18): the primitives, transports and lifecycle used in §7.
- OpenAI / provider docs for tool calling and OpenAI-compatible endpoints (`tools`,
  `tool_choice`, `tool_calls`, `tool_call_id` shapes) used in §2–§3.
- Practical agent-building guides, 2025–2026 ("build an agent in ~60 lines of Python
  against a local Ollama endpoint"; memory-tier and "cheap models poison memory"
  observations) — used in §2, §4, §6, §8.
- OpenClaw project docs (self-hosted personal agent: workspace layout, `SOUL.md` /
  `USER.md` / `IDENTITY.md`, cron, TUI + gateway, VPS sizing) — used in §5, §8.
- MCP server design write-ups (2026): token cost of tool schemas, `limit`/`orderBy`,
  error semantics, rate-limiting — used in §3, §7, §9.

*Kept deliberately short of "best practice" fashion. If a claim here is not in the repo
as working code, treat it as an opinion.*
