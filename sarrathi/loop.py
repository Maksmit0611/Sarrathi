"""
loop.py — the agent loop.

This is the difference between an app and an agent, in about 60 lines:

    APP      question  ->  answer                          (one shot, stateless)
    AGENT    goal -> think -> call a tool -> observe -> think again -> ... -> done
                     ^                          |
                     +--------------------------+
                     (and it writes down what it learned)

The loop keeps going until the model stops asking for tools, or a step budget is
reached. Every tool call is logged, so you can audit exactly what your agent did
and why - which is the thing that makes an agent trustworthy rather than magic.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from . import identity, tools as toolkit
from .memory import AgentMemory, set_home
from idea_oracle.brain import OfflineBrain

MAX_STEPS = 8


@dataclass
class Step:
    n: int
    tool: str
    arguments: dict
    result: str
    duration_ms: int


@dataclass
class Turn:
    goal: str
    answer: str
    steps: list[Step] = field(default_factory=list)
    stopped_reason: str = "finished"
    elapsed_ms: int = 0
    brain: str = ""


class Agent:
    """
    Sarathi — the charioteer.

    Not a website. A process that runs where you run, remembers what you tell it,
    and has tools it can actually use.
    """

    def __init__(self, brain=None, home=None, verbose: bool = True, max_steps: int = MAX_STEPS):
        if home:
            home_path = set_home(home)   # tools and memory must agree on one home
            if not os.environ.get("SARRATHI_WORKSPACE"):
                toolkit.WORKSPACE = Path(home_path).resolve()
        self.memory = AgentMemory(home)
        self.identity = identity.load(self.memory.home)
        self.brain = brain
        self.verbose = verbose
        self.max_steps = max_steps
        self.offline = brain is None or isinstance(brain, OfflineBrain)

    # -- system prompt -----------------------------------------------------
    def system_prompt(self, goal: str = "") -> str:
        mem_block = self.memory.context_block(goal)
        base = identity.system_prompt(self.identity)
        from .tools import REGISTRY
        tool_lines = "\n".join(f"- {t.name}({', '.join(t.parameters.get('properties', {}))}): {t.description}"
                               for t in REGISTRY.values())
        return (
            f"{base}\n\n"
            f"## Tools you can call\n{tool_lines}\n\n"
            f"## How to work\n"
            f"1. If the user mentions a business idea, market, or a place, call `shodh_research` before answering.\n"
            f"2. Call `recall` before asking the user for something they may have told you before.\n"
            f"3. Call `remember` when you learn something durable. Do not remember small talk.\n"
            f"4. You may call several tools in sequence. After each result, decide whether you need another.\n"
            f"5. When you have enough, answer the user directly and briefly. Cite file paths you produced.\n"
            f"6. Never claim you did something you did not do with a tool. Never invent file paths.\n"
            + (f"\n## Memory about this user\n{mem_block}\n" if mem_block else "")
        )

    # -- one turn ----------------------------------------------------------
    def turn(self, goal: str, history: list[dict] | None = None) -> Turn:
        started = time.time()
        goal = (goal or "").strip()
        if not goal:
            return Turn(goal="", answer="I need something to work on.", brain="none")

        self.memory.log_turn("user", goal)

        if self.offline:
            turn = self._offline_turn(goal)
        else:
            turn = self._llm_turn(goal, history or [])

        turn.elapsed_ms = int((time.time() - started) * 1000)
        turn.brain = getattr(self.brain, "label", "offline")
        self.memory.log_turn("agent", turn.answer[:2000])
        return turn

    # -- the real loop -----------------------------------------------------
    def _llm_turn(self, goal: str, history: list[dict]) -> Turn:
        messages: list[dict] = [{"role": "system", "content": self.system_prompt(goal)}]
        messages.extend(history[-8:])          # short-term memory: recent turns
        messages.append({"role": "user", "content": goal})

        steps: list[Step] = []
        schemas = toolkit.schemas()

        for n in range(1, self.max_steps + 1):
            msg = self._chat(messages, schemas)
            if msg is None:
                return Turn(goal=goal, answer=self._fallback(goal, steps),
                            steps=steps, stopped_reason="brain error")

            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                return Turn(goal=goal, answer=msg.get("content", "") or "(no answer)",
                            steps=steps, stopped_reason="finished")

            messages.append({"role": "assistant", "content": msg.get("content") or "",
                             "tool_calls": tool_calls})

            for call in tool_calls:
                fn = call.get("function", {})
                name = fn.get("name", "")
                args = fn.get("arguments", "{}")
                t0 = time.time()
                if self.verbose:
                    preview = args if isinstance(args, str) else json.dumps(args)
                    print(f"  ↳ {name}({preview[:110]})", file=sys.stderr)
                result = toolkit.execute(name, args)
                dt = int((time.time() - t0) * 1000)
                try:
                    parsed = json.loads(args) if isinstance(args, str) else (args or {})
                except json.JSONDecodeError:
                    parsed = {}
                steps.append(Step(n, name, parsed, result[:2000], dt))
                if self.verbose:
                    first = result.splitlines()[0][:110] if result else "(empty)"
                    print(f"    ✓ {first}  [{dt}ms]", file=sys.stderr)
                messages.append({"role": "tool", "tool_call_id": call.get("id", name),
                                 "content": result[:6000]})

        return Turn(goal=goal, answer=self._fallback(goal, steps), steps=steps,
                    stopped_reason=f"hit step limit ({self.max_steps})")

    def _chat(self, messages: list[dict], schemas: list[dict]) -> dict | None:
        """Call the brain with tool schemas; tolerate providers that differ slightly."""
        fn = getattr(self.brain, "chat_tools", None)
        if fn is None:
            return {"role": "assistant",
                    "content": self.brain.chat(messages[0]["content"], messages[-1]["content"])}
        try:
            return fn(messages, schemas)
        except Exception as exc:  # noqa: BLE001
            if self.verbose:
                print(f"  ! brain error: {type(exc).__name__}: {exc}", file=sys.stderr)
            return None

    # -- offline: the agent still works with no LLM and no money -----------
    CITIES = {
        "australia": ["melbourne", "sydney", "brisbane", "perth", "adelaide", "dandenong",
                      "geelong", "canberra", "hobart", "darwin", "auckland"],
        "india": ["bengaluru", "bangalore", "mumbai", "delhi", "chennai", "hyderabad", "pune",
                  "kolkata", "ahmedabad", "jaipur"],
        "indonesia": ["jakarta", "surabaya", "bandung"],
        "united states": ["new york", "san francisco", "austin", "chicago", "seattle", "boston",
                          "los angeles", "denver", "atlanta"],
        "united kingdom": ["london", "manchester", "birmingham", "edinburgh", "leeds"],
        "kenya": ["nairobi", "mombasa"],
        "nigeria": ["lagos", "abuja"],
        "brazil": ["sao paulo", "são paulo", "rio de janeiro"],
        "germany": ["berlin", "munich", "hamburg", "frankfurt"],
        "japan": ["tokyo", "osaka", "kyoto"],
    }

    def _detect_country(self, low: str) -> str:
        """
        Prefer the place the user is heading *to* over the place they are *in*.
        "I live in Melbourne and want to open a tiffin service in Bengaluru" must read
        as India, not Australia. Heuristic: the last place named after in/to/at wins.
        """
        candidates: list[tuple[int, str]] = []
        for country, cities in self.CITIES.items():
            for city in cities:
                for idx in [m.start() for m in re.finditer(re.escape(city), low)]:
                    candidates.append((idx, country))
            for idx in [m.start() for m in re.finditer(re.escape(country), low)]:
                candidates.append((idx, country))
        if not candidates:
            for c in ("italy", "france", "spain", "china", "singapore", "canada", "mexico",
                      "sweden", "saudi arabia", "uae", "new zealand", "netherlands",
                      "philippines", "vietnam", "kenya", "nigeria", "brazil", "germany", "japan"):
                if c in low:
                    return c.title()
            return ""
        prepositional = [(i, c) for i, c in candidates
                         if low[max(0, i - 5):i].strip().endswith(("in", "to", "at", "into"))]
        return (prepositional[-1][1] if prepositional else candidates[0][1]).title()

    def _offline_turn(self, goal: str) -> Turn:
        """
        No model available, so route the request with rules. This is why the agent is
        never useless: research, memory and file work all still function. With a model,
        the same toolset is chosen by the model instead.
        """
        low = goal.lower()
        steps: list[Step] = []

        def run(name: str, args: dict) -> str:
            t0 = time.time()
            if self.verbose:
                print(f"  ↳ {name}({json.dumps(args)[:100]})", file=sys.stderr)
            res = toolkit.execute(name, args)
            steps.append(Step(len(steps) + 1, name, args, res[:2000], int((time.time() - t0) * 1000)))
            return res

        # 0. learn first - durable self-descriptions are stored even with no model
        captured = self._offline_capture(goal, run)

        # 1. explicit /slash commands
        if low.startswith("/"):
            cmd, _, rest = goal[1:].partition(" ")
            cmd, rest = cmd.strip().lower(), rest.strip()
            routes = {
                "research": ("shodh_research", lambda: {"idea": rest or "unspecified idea",
                                                        "country": self._detect_country(rest.lower())}),
                "shodh": ("shodh_research", lambda: {"idea": rest or "unspecified idea",
                                                     "country": self._detect_country(rest.lower())}),
                "idea": ("shodh_research", lambda: {"idea": rest or "unspecified idea",
                                                    "country": self._detect_country(rest.lower())}),
                "remember": ("remember", lambda: {"text": rest, "kind": "fact", "tags": []}),
                "recall": ("recall", lambda: {"query": rest}),
                "memory": ("memory_stats", lambda: {}),
                "skills": ("list_skills", lambda: {}),
                "ls": ("list_dir", lambda: {"path": rest or "."}),
            }
            if cmd in routes:
                tool_name, args_fn = routes[cmd]
                return Turn(goal, run(tool_name, args_fn()), steps, brain="offline")
            if cmd in ("help", "?"):
                return Turn(goal, HELP_TEXT, steps, brain="offline")

        # 2. store a memory
        if any(w in low for w in ("remember", "note that", "keep in mind", "don't forget")):
            text = goal
            for marker in ("remember that", "remember", "note that", "keep in mind that",
                           "keep in mind", "don't forget that", "don't forget"):
                idx = low.find(marker)
                if idx != -1:
                    text = goal[idx + len(marker):].strip(" :,-")
                    break
            return Turn(goal, run("remember", {"text": text, "kind": "fact", "tags": []}), steps,
                        brain="offline")

        # 3. ask about memory / identity - checked before research, because these are questions
        # a task is a task: "remind me to X" stores work, it does not search memory
        if any(w in low for w in ("remind me to", "todo:", "i need to ", "follow up on", "don't let me forget")):
            text = goal
            for marker in ("remind me to", "todo:", "i need to", "follow up on", "don't let me forget"):
                idx = low.find(marker)
                if idx != -1:
                    text = goal[idx + len(marker):].strip(" :,-") or goal
                    break
            return Turn(goal, run("remember", {"text": text, "kind": "task", "tags": ["todo"]}), steps,
                        brain="offline")

        recall_triggers = ("what do you know", "what do you remember", "do you remember", "recall",
                           "search memory", "tell me about", "what have you got on", "my details",
                           "who am i", "what do i know", "remind me what", "remind me about")
        if any(w in low for w in recall_triggers) and "business idea" not in low:
            query = goal
            for marker in ("what do you know about", "what do you remember about", "tell me about",
                           "remind me about", "what have you got on"):
                idx = low.find(marker)
                if idx != -1:
                    query = goal[idx + len(marker):].strip(" ?:,.")
                    break
            return Turn(goal, run("recall", {"query": query}), steps, brain="offline")

        # 4. research a business idea
        research_words = ("research", "investigate", "analyse", "analyze", "validate", "vet",
                          "would it work", "will it work", "worth doing", "should i",
                          "market entry", "go to market", "idea", "business", "startup",
                          "start a", "start an", "open a", "open an", "market", "expand",
                          "export", "launch", "shop", "cafe", "restaurant", "app", "service",
                          "sell", "franchise", "product")
        if any(w in low for w in research_words):
            country = self._detect_country(low)
            return Turn(goal, run("shodh_research", {"idea": goal, "country": country}), steps,
                        brain="offline")

        # 5. we still learned something even if we could not answer
        if captured:
            return Turn(goal, f"Noted and saved: {captured}\n\n"
                              f"Ask me about it any time (/recall) or give me an idea to research.",
                        steps, brain="offline")

        return Turn(
            goal,
            "I'm running without an LLM brain right now, so I can only do the things I have tools for.\n\n"
            "Try:\n"
            "  /research a tiffin service in Bengaluru with no budget\n"
            "  /remember Max is based in Melbourne and has no capital\n"
            "  /recall budget\n"
            "  /skills\n"
            "  /ls\n\n"
            "Add a free API key (GROQ_API_KEY, GEMINI_API_KEY or OPENROUTER_API_KEY) and I'll "
            "reason, plan and chain tools myself.",
            steps, brain="offline")

    def _offline_capture(self, goal: str, run) -> str:
        """
        Rule-based memory extraction. Crude, but it means the agent gets smarter every
        session even on a $0, no-model setup. With a model, `remember` does this properly.

        Two details that matter: the stored fact drops the trigger phrase ("remind me to
        check X" is stored as "check X"), and one sentence can yield several facts -
        "I live in Melbourne and have no budget" is two things worth knowing.
        """
        low = goal.lower()
        triggers = (
            ("person", ("my name is", "i am based in", "i'm based in", "i live in", "i work in", "i am in ")),
            ("preference", ("i prefer", "i like", "i hate", "i don't like", "i don't want", "i always")),
            ("decision", ("i decided", "i've decided", "we decided", "i will not", "i won't", "i refuse")),
            ("fact", ("i run", "i own", "my business", "i am building", "i'm building", "my company")),
            ("idea", ("i want to start", "i'm thinking of starting", "i want to launch", "my idea is")),
            ("task", ("remind me to", "todo:", "i need to", "follow up on")),
        )
        found: list[tuple[int, int, str, str]] = []   # (start, end, kind, text)
        for kind, markers in triggers:
            for marker in markers:
                for m in re.finditer(re.escape(marker), low):
                    idx = m.start()
                    # substance, not the trigger phrase
                    body = goal[idx + len(marker):].strip(" :,-")
                    lead = goal[idx:idx + len(marker)]
                    if len(body) < 12:
                        continue
                    # stop at the next clause so one fact stays one fact
                    for cut in (" and ", ", ", " but ", " so ", " because ", ". ", "; "):
                        pos = body.find(cut)
                        if pos > 8:
                            body = body[:pos]
                            break
                    body = body.strip(" .,:;-")
                    if len(body) >= 3:
                        # a location or a preference reads better as a sentence
                        # ("I live in Melbourne"); a task reads better bare ("check the lease")
                        text = body if kind == "task" else f"{lead} {body}".strip()
                        found.append((idx, idx + len(marker) + len(body), kind, text))
        # drop overlapping matches (e.g. "i am in" inside "i am based in")
        found.sort(key=lambda f: (f[0], -(f[1] - f[0])))
        kept: list[tuple[int, int, str, str]] = []
        for f in found:
            if any(not (f[1] <= k[0] or f[0] >= k[1]) for k in kept):
                continue
            kept.append(f)
        for _, _, kind, body in kept[:3]:
            run("remember", {"text": body[0].upper() + body[1:] if body else body,
                             "kind": kind, "tags": []})
        return kept[0][3] if kept else ""

    # -- graceful degradation ---------------------------------------------
    @staticmethod
    def _fallback(goal: str, steps: list[Step]) -> str:
        if not steps:
            return ("I couldn't reach a model, and no tool matched this request. "
                    "Check your API key or ask me something I have a tool for (`/help`).")
        produced = [s.result.splitlines()[0] for s in steps if s.result]
        return ("I couldn't finish reasoning (the model became unavailable), but the work I did "
                "before that is saved:\n\n" + "\n".join(f"- {s.tool}: {p}" for s, p in zip(steps, produced)))


HELP_TEXT = """Sarathi — commands

  /research <idea>        run a Shodh and produce an Arthabodh (a full report on disk)
  /remember <something>   store a durable fact about you or your business
  /recall <topic>         search everything I remember
  /memory                memory stats and where it lives
  /skills                list installed skills (metadata only - cheap)
  /ls [path]             list files
  /help                  this

  Anything else is handled by the agent loop: with a model key set, I plan and
  chain tools myself. Without one, I route by keyword and still do real work.

  exit / ctrl-D          leave (memory and reports persist)
"""
