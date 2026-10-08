# agent_workspace — the agent's home

This is an **example agent home**, checked into the repo so you can see the shape of
one. Copy it, or point the agent at your own directory:

```bash
python3 agent.py --home agent_workspace      # lives and works here
python3 agent.py                             # lives in ~/.sarrathi, works in the cwd
```

```
identity/     IDENTITY.md (name, role) · SOUL.md (rules) · USER.md (about you)
memory/       facts.jsonl (the real store) · MEMORY.md (readable digest) · sessions/ (turn logs)
reports/      finished work the agent produced
logs/         scheduled-run archives
arthabodh-reports/   full Arthabodh reports written by the Shodh engine
```

Nothing here is sacred. `SOUL.md` is the file that actually changes behaviour —
edit it and the agent's next session behaves differently. Delete `facts.jsonl` and it
forgets everything, cleanly.

`memory/MEMORY.md` is regenerated on every write, so you can read what your agent
believes about you without decoding a database.
