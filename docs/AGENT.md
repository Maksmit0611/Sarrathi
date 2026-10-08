# Sarathi — the agent

**An app waits for someone to visit it. Sarathi runs.**

Sarathi is a business-research agent that lives on your machine. It remembers what you
tell it, has tools it can actually use, and can work while you sleep. It costs nothing
to run: with no API key it still researches, remembers and writes reports; with a free
key it plans and chains tools on its own.

```bash
cd sarathi-labs
python3 agent.py                        # interactive session
python3 agent.py "research a home tiffin service in Bengaluru with no budget"
python3 agent.py --help                 # everything else
```

No install. No dependencies. Python 3.10+.

---

## 60-second tour

```
$ python3 agent.py

   ▄▄▄▄▄▄▄   Sarathi  सारथि
  █ ☸     █  the charioteer — your research agent
  █  ▄▄▄  █
  █  ███  █  Sarathi Labs · engine: Shodh · delivers: Arthabodh
   ▀▀▀▀▀▀▀

  brain      : offline (no model — tools still work)
  tools      : 13
  memory     : 0 facts · 0 sessions · /home/you/.sarrathi
  workspace  : /home/you/sarathi-labs

you › I want to open a cafe in Dandenong
  ↳ remember({"text": "I want to open a cafe in Dandenong", "kind": "idea"})
  ↳ shodh_research({"idea": "I want to open a cafe in Dandenong", "country": "Australia"})
sarathi › Arthabodh written to ~/.sarrathi/arthabodh-reports/20261008-i-want-to-open-a-cafe-in-dandenong.md
          Market: Australia | Sector: food | Risk flags: [medium] short-term orientation...
```

Next session:

```
you › what do you know about my business
sarathi › [idea] 2026-10-08 — I want to open a cafe in Dandenong
```

That is the difference. It remembered, without being told to.

---

## Commands

| Command | What it does |
|---|---|
| `/research <idea>` | run Shodh, write a full Arthabodh to disk |
| `/remember <text>` | store a durable fact |
| `/recall <topic>` | search everything it remembers |
| `/memory` | how many memories, by type, and where |
| `/skills` | list installed skills (metadata only — cheap) |
| `/ls [path]` | list files |
| `/help` | command list |

Anything else goes to the agent loop: with a model, it decides which tools to use.
Without one, it routes by intent — and still learns from what you say.

## Flags

| Flag | Why you'd use it |
|---|---|
| `--home DIR` | the agent lives **and works** here (default `~/.sarrathi`, working dir = cwd) |
| `--workspace DIR` | separate the working directory from the agent's home |
| `--offline` | force tools-only mode |
| `--tools` | print every tool, its arguments and its danger rating |
| `--memory` / `--identity` | inspect what it knows / who it is |
| `--providers` | which free brains are available in this environment |
| `--json` | machine-readable output for pipes and scripts |
| `--mcp` / `--mcp-list` | connect MCP servers from `mcp.json` |
| `--queue "<goal>"` → `--watch` | unattended runs (cron) |
| `--quiet` | hide the tool-call trace |

---

## Give it a brain (still $0)

```bash
export GROQ_API_KEY=gsk_...          # free, no card — console.groq.com
# or GEMINI_API_KEY, OPENROUTER_API_KEY, NVIDIA_API_KEY, MISTRAL_API_KEY
python3 agent.py --providers         # see what it detects
python3 agent.py                     # now it plans and chains tools itself
```

Fully local, no keys at all:

```bash
ollama pull qwen2.5:7b
ollama serve
python3 agent.py
```

The agent picks up a local Ollama endpoint automatically. Small local models work, with
the caveat in `docs/BUILDING_AN_AGENT.md` §6: keep the tasks narrow.

---

## Run it unattended

```bash
python3 agent.py --queue "research a tiffin service in Bengaluru, no budget"
python3 agent.py --queue "check whether the cafe idea fits Australian culture"

# run the queue now, archive the results, exit
python3 agent.py --watch

# or every Monday at 8am
crontab -e
0 8 * * 1  cd /path/to/sarathi-labs && python3 agent.py --watch >> ~/.sarrathi/logs/cron.log 2>&1
```

Each run is archived to `~/.sarrathi/logs/watch-<timestamp>.json` with the goal, the
answer and the tool calls it made. An unattended agent that cannot explain itself is not
a feature.

---

## Connect MCP servers (new abilities, no new code)

```bash
cp mcp.json.example mcp.json     # edit to taste
python3 agent.py --mcp-list
python3 agent.py --mcp
```

Their tools appear as `mcp__<server>__<tool>` alongside the native ones. See
`docs/BUILDING_AN_AGENT.md` §7 for what MCP is and how to write your own server.

---

## Change its personality

Behaviour lives in three editable files, not in the source code:

```
~/.sarrathi/identity/IDENTITY.md   name, role, vibe
~/.sarrathi/identity/SOUL.md       the rules — edit this to change behaviour
~/.sarrathi/identity/USER.md       about you (the agent fills this in)
```

Edit `SOUL.md`, and the next session behaves differently. That is the whole configuration
system.

---

## What it can do (tools)

| Tool | Danger | What it does |
|---|---|---|
| `shodh_research` | safe | full Arthabodh: cultural fit, what worked, what failed, risk flags, 7-day $0 plan |
| `remember` / `recall` / `memory_stats` | safe | durable memory across sessions |
| `read_file` / `write_file` / `list_dir` | safe | files, scoped to the workspace |
| `fetch_url` | safe | web pages, stripped to readable text |
| `run_shell` | **guarded** | allow-listed commands only; deny-list refuses `rm -rf`, `sudo`, … |
| `list_skills` / `load_skill` | safe | progressive disclosure: metadata first, full text only when needed |
| `now` / `save_report` | safe | time; save finished work as markdown |

Add your own: one function, one `Tool(...)` entry in `sarrathi/tools.py::REGISTRY`. It is
available to the model immediately.

---

## Files it keeps

```
~/.sarrathi/
├── identity/          IDENTITY.md · SOUL.md · USER.md
├── memory/
│   ├── facts.jsonl    the source of truth — append-only, one fact per line
│   ├── MEMORY.md      human-readable digest, regenerated on every write
│   └── sessions/      daily turn logs
├── arthabodh-reports/ full reports produced by Shodh
├── reports/           reports saved via save_report
├── logs/              archives from --watch runs
└── queue.jsonl        pending tasks for the next run
```

Delete `facts.jsonl` and it forgets everything, cleanly. Grep it to see exactly what it
knows. Diff it in git. No database, nothing hidden.

---

## Tests

```bash
python3 tests/test_agent.py     # 77 checks — memory, tools, the loop, offline mode, MCP, identity
python3 tests/test_intake.py    # 63 checks — the Shodh engine and report contract
```

Both run offline, on the standard library, with no API key. The agent loop is verified
against a mock brain, so tool calling is tested without spending a cent.

---

## How it fits together

```
agent.py          ← you run this
   │
   ├── sarrathi/loop.py       the agent loop: think → tool → observe → repeat
   ├── sarrathi/tools.py      what it can do (13 tools, danger-rated)
   ├── sarrathi/memory.py     what it remembers (3 tiers, append-only)
   ├── sarrathi/identity.py   who it is (editable markdown)
   ├── sarrathi/mcp_bridge.py other people's tools (JSON-RPC over stdio)
   │
   └── idea_oracle/           the Shodh engine — retrieval, cases, cultures, flags
             └── Arthabodh    the report it delivers
```

**Sarathi Labs** the lab · **Sarathi** the agent · **Shodh** the engine · **Arthabodh**
the deliverable · **Arthashastra** the lineage.

The theory behind all of this is in `docs/BUILDING_AN_AGENT.md` — read that if you want
to build your own rather than use this one.
