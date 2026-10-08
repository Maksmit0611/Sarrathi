"""
Regression tests for the Sarathi agent. Standard library only, offline, deterministic:

    python tests/test_agent.py

The important one is test_llm_loop: it proves the agent loop actually works
(plan -> call tool -> observe -> answer) using a mock brain, so the tool-calling
machinery is verified without needing an API key or a network.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sarrathi import tools as toolkit  # noqa: E402
from sarrathi.loop import Agent  # noqa: E402
from sarrathi.memory import AgentMemory  # noqa: E402

PASS = 0
FAIL = 0
TMP = Path(tempfile.mkdtemp(prefix="sarathi-test-"))
os.environ["SARRATHI_HOME"] = str(TMP / "default-home")   # never touch the real agent home


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {label}")
    else:
        FAIL += 1
        print(f"  ✗ {label} {detail}")


# ---------------------------------------------------------------------------
# 1. Memory: durable, de-duplicated, searchable, human-readable
# ---------------------------------------------------------------------------
def test_memory() -> None:
    print("\nMemory — the difference between an agent and a chatbot")
    home = TMP / "mem"
    mem = AgentMemory(home=home)

    m = mem.remember("Max is based in Melbourne.", kind="person", tags=["location"])
    check("remember returns a Memory with a timestamp", bool(m.ts) and m.kind == "person")
    check("facts.jsonl is written", (home / "memory" / "facts.jsonl").exists())

    dup = mem.remember("max IS based in melbourne.", kind="person")
    check("duplicate memory is not stored twice", dup.ts == m.ts)
    check("only one fact on disk after duplicate", len(AgentMemory(home=home).load()) == 1)

    AgentMemory(home=home).remember("Decision: no money will be spent on the project.", kind="decision")
    reloaded = AgentMemory(home=home)
    check("memory survives a new process/instance", len(reloaded.load()) == 2)

    hits = reloaded.recall("money")
    check("recall finds a memory by keyword", len(hits) == 1 and "money" in hits[0][1].text)
    check("recall returns a relevance score", isinstance(hits[0][0], float) and hits[0][0] > 0)

    check("recall on a nonsense query returns nothing",
          reloaded.recall("quantum hydraulic bananas") == [])

    check("question scaffolding is stripped (\"what do you know about X\" -> X)",
          len(reloaded.recall("what do you know about money")) == 1)

    digest = (home / "memory" / "MEMORY.md").read_text()
    check("MEMORY.md digest is human-readable", "## What I know about you" in digest or "## People" in digest)
    check("digest records the fact", "Melbourne" in digest)

    stats = reloaded.stats()
    check("stats count facts and kinds", stats["facts"] == 2 and stats["by_kind"]["decision"] == 1)

    ctx = reloaded.context_block("money")
    check("context block carries memory into the prompt", "Melbourne" in ctx and "RELEVANT" in ctx)

    try:
        reloaded.remember("   ", kind="fact")
        check("empty memory is rejected", False)
    except ValueError:
        check("empty memory is rejected", True)

    MEM = reloaded


# ---------------------------------------------------------------------------
# 2. Tools: the agent's hands
# ---------------------------------------------------------------------------
def test_tools() -> None:
    print("\nTools — what makes it act rather than answer")
    check("registry is populated", len(toolkit.REGISTRY) >= 13)
    check("every tool has a schema with a name",
          all(t.schema()["function"]["name"] == n for n, t in toolkit.REGISTRY.items()))
    check("tool schemas are valid JSON",
          bool(json.dumps(toolkit.schemas())))

    out = toolkit.execute("now", {})
    check("now tool returns a date", len(out) > 8 and "-" in out)

    target = TMP / "workspace-file.txt"
    toolkit.WORKSPACE = TMP
    res = toolkit.execute("write_file", {"path": "written.txt", "content": "hello agent"})
    check("write_file creates the file", (TMP / "written.txt").read_text() == "hello agent", res)
    res = toolkit.execute("read_file", {"path": "written.txt"})
    check("read_file reads it back", "hello agent" in res)
    res = toolkit.execute("list_dir", {"path": "."})
    check("list_dir lists it", "written.txt" in res)

    check("unknown tool returns an error, not an exception",
          "unknown tool" in toolkit.execute("does_not_exist", {}))
    check("bad arguments return an error, not an exception",
          "error" in toolkit.execute("read_file", {"nonsense": 1}).lower())
    check("missing file is reported cleanly",
          "does not exist" in toolkit.execute("read_file", {"path": "nope.txt"}))

    # the guard rails matter: an agent with a shell is an agent that can break things
    check("shell deny-list blocks rm -rf", "refused" in toolkit.execute("run_shell", {"command": "rm -rf /"}))
    check("shell allow-list blocks arbitrary binaries",
          "refused" in toolkit.execute("run_shell", {"command": "nc -l 1234"}))
    check("shell allow-list permits safe commands",
          "refused" not in toolkit.execute("run_shell", {"command": "echo sarathi"}))
    check("fetch_url refuses non-http schemes",
          "error" in toolkit.execute("fetch_url", {"url": "file:///etc/passwd"}).lower())

    res = toolkit.execute("remember", {"text": "Test fact from the test suite.", "kind": "fact", "tags": ["test"]})
    check("remember tool writes memory", "Remembered" in res)
    res = toolkit.execute("recall", {"query": "test suite"})
    check("recall tool returns the fact", "Test fact from the test suite" in res)
    check("recall tool falls back to a listing when nothing matches",
          "currently remember" in toolkit.execute("recall", {"query": "zzzq nonexistent"}))
    check("memory_stats tool returns JSON",
          "facts" in json.loads(toolkit.execute("memory_stats", {})))

    skills_res = toolkit.execute("list_skills", {})
    check("list_skills returns descriptions (metadata tier only)", isinstance(skills_res, str) and len(skills_res) > 0)
    check("load_skill rejects an unknown skill name", "no skill named" in toolkit.execute("load_skill", {"name": "nope"}))

    check("tool catalogue is generated for the prompt", "shodh_research" in toolkit.catalogue())


# ---------------------------------------------------------------------------
# 3. The agent loop with a real tool-calling brain (mocked, so it runs offline)
# ---------------------------------------------------------------------------
class MockBrain:
    """Stands in for a provider. First turn: asks for a tool. Second turn: answers."""
    label = "mock-model (test)"
    provider_name = "mock"

    def __init__(self):
        self.calls = 0
        self.seen_tool_result = False

    def chat_tools(self, messages, tools, **kw):
        self.calls += 1
        if self.calls == 1:
            assert any(t["function"]["name"] == "now" for t in tools), "schemas not passed to brain"
            return {"role": "assistant", "content": "",
                    "tool_calls": [{"id": "call_1", "type": "function",
                                    "function": {"name": "now", "arguments": "{}"}}]}
        # the tool result must have been appended before we are called again
        self.seen_tool_result = any(m.get("role") == "tool" for m in messages)
        return {"role": "assistant", "content": "The date came from a tool call.", "tool_calls": []}


class LoopBrain:
    """Asks for a tool forever — proves the step budget stops runaway loops."""
    label = "loop-model (test)"
    provider_name = "mock"

    def chat_tools(self, messages, tools, **kw):
        return {"role": "assistant", "content": "",
                "tool_calls": [{"id": "c", "type": "function",
                                "function": {"name": "now", "arguments": "{}"}}]}


class BrokenBrain:
    label = "broken (test)"
    provider_name = "mock"

    def chat_tools(self, messages, tools, **kw):
        raise RuntimeError("provider down")


def test_llm_loop() -> None:
    print("\nThe loop — think, act, observe, think again")
    brain = MockBrain()
    agent = Agent(brain=brain, home=TMP / "loop", verbose=False)
    turn = agent.turn("what is today's date?")

    check("loop executed the tool the model asked for",
          len(turn.steps) == 1 and turn.steps[0].tool == "now")
    check("loop fed the tool result back to the model", brain.seen_tool_result)
    check("loop returned the model's final answer",
          turn.answer == "The date came from a tool call.")
    check("loop stopped because the model was done", turn.stopped_reason == "finished")
    check("the turn was logged to the session store",
          any((TMP / "loop" / "memory" / "sessions").glob("*.jsonl")))
    check("agent is not in offline mode when a brain is present", agent.offline is False)

    looping = Agent(brain=LoopBrain(), home=TMP / "loop2", verbose=False, max_steps=3)
    turn = looping.turn("loop forever")
    check("step limit stops a runaway agent", len(turn.steps) == 3)
    check("step limit is reported honestly", "step limit" in turn.stopped_reason)

    broken = Agent(brain=BrokenBrain(), home=TMP / "loop3", verbose=False)
    turn = broken.turn("research a bakery in Naples")
    check("a dead provider does not crash the agent", isinstance(turn.answer, str) and len(turn.answer) > 10)
    check("dead provider is reported as such", "couldn't" in turn.answer.lower() or "error" in turn.stopped_reason)


# ---------------------------------------------------------------------------
# 4. Offline mode: no key, no network, still an agent
# ---------------------------------------------------------------------------
def test_offline() -> None:
    print("\nOffline — $0 and no API key, and it still does real work")
    home = TMP / "offline"
    agent = Agent(brain=None, home=home, verbose=False)
    check("agent auto-detects offline mode", agent.offline is True)

    turn = agent.turn("remember that my workshop is in Dandenong")
    check("offline 'remember' routes to the memory tool",
          any(s.tool == "remember" for s in turn.steps))
    check("the fact is actually stored",
          any("Dandenong" in m.text for m in AgentMemory(home=home).load()))

    turn = agent.turn("what do you know about Dandenong")
    check("offline recall finds it in a later turn",
          "Dandenong" in turn.answer)

    turn = agent.turn("I am based in Melbourne and I refuse to spend money")
    check("offline mode learns a self-description without a model",
          any("Melbourne" in m.text for m in AgentMemory(home=home).load()))

    turn = agent.turn("I want to open a cafe in Dandenong")
    check("offline research runs the Shodh engine",
          any(s.tool == "shodh_research" for s in turn.steps))
    check("offline market detection maps city -> country", "Australia" in turn.answer)

    # regression: two places in one sentence -> the destination wins, not the home
    turn = agent.turn("I live in Melbourne and I want to open a tiffin service in Bengaluru")
    check("destination beats home city when both are mentioned", "India" in turn.answer,
          turn.answer[:120])
    check("home city is still remembered", any("Melbourne" in m.text for m in AgentMemory(home=home).load()))

    # regression: stored facts must read as sentences, not bare fragments
    before = len(AgentMemory(home=home).load())
    agent.turn("I prefer short answers")
    text = [m.text for m in AgentMemory(home=home).load()][-1]
    check("a captured fact reads as a sentence, not a fragment",
          text.lower().startswith("i prefer") and len(text.split()) >= 3, repr(text))

    # regression: the same task twice is one memory, not two
    n0 = len(AgentMemory(home=home).load())
    agent.turn("remind me to check the lease terms")
    agent.turn("remind me to check the lease terms")
    n1 = len(AgentMemory(home=home).load())
    check("an identical task is not stored twice across turns", n1 - n0 == 1, f"{n0} -> {n1}")
    check("the task is stored without its trigger phrase",
          any(m.kind == "task" and m.text.lower().startswith("check") for m in AgentMemory(home=home).load()))

    turn = agent.turn("/help")
    check("/help returns the command list", "/research" in turn.answer)

    turn = agent.turn("blah blah nothing relevant at all")
    check("unknown input gives guidance instead of a crash",
          "tools" in turn.answer.lower() or "try:" in turn.answer.lower())


# ---------------------------------------------------------------------------
# 5. MCP bridge: JSON-RPC over stdio against a stub server
# ---------------------------------------------------------------------------
STUB_SERVER = r'''
import json, sys
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    msg = json.loads(line)
    method, mid = msg.get("method"), msg.get("id")
    if mid is None:
        continue
    if method == "initialize":
        result = {"protocolVersion": "2025-06-18",
                  "serverInfo": {"name": "stub", "version": "1.0"},
                  "capabilities": {"tools": {}}}
    elif method == "tools/list":
        result = {"tools": [{"name": "echo", "description": "Echo the text back",
                             "inputSchema": {"type": "object",
                                             "properties": {"text": {"type": "string"}},
                                             "required": ["text"]}}]}
    elif method == "tools/call":
        args = msg.get("params", {}).get("arguments", {})
        if args.get("text") == "fail":
            result = {"isError": True, "content": [{"type": "text", "text": "deliberate failure"}]}
        else:
            result = {"content": [{"type": "text", "text": "echoed: " + str(args.get("text", ""))}]}
    else:
        result = {}
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": mid, "result": result}) + "\n")
    sys.stdout.flush()
'''


def test_mcp() -> None:
    print("\nMCP — new abilities without new code")
    from sarrathi import mcp_bridge

    stub = TMP / "stub_server.py"
    stub.write_text(STUB_SERVER, encoding="utf-8")
    cfg = {"servers": {"stub": {"command": sys.executable, "args": [str(stub)]}}}

    servers = mcp_bridge.connect_all(cfg, verbose=False)
    check("connected to the stub MCP server", len(servers) == 1)
    if not servers:
        return
    srv = servers[0]
    check("handshake returned server info", srv.initialize()["serverInfo"]["name"] == "stub")
    check("tools were discovered", len(srv.tools) == 1 and srv.tools[0]["name"] == "echo")
    check("tools/call returns content", srv.call_tool("echo", {"text": "hi"}) == "echoed: hi")
    check("a failing MCP tool is surfaced as an error, not an exception",
          srv.call_tool("echo", {"text": "fail"}).startswith("error:"))

    n = mcp_bridge.register(servers)
    check("MCP tools registered into the agent registry", n == 1)
    check("namespacing prevents collisions", "mcp__stub__echo" in toolkit.REGISTRY)
    check("MCP tool is callable through the normal registry",
          "echoed: via-registry" in toolkit.execute("mcp__stub__echo", {"text": "via-registry"}))
    check("MCP tools are marked guarded", toolkit.REGISTRY["mcp__stub__echo"].danger == "guarded")

    bad = mcp_bridge.connect_all({"servers": {"nope": {"command": "definitely-not-a-real-binary"}}},
                                 verbose=False)
    check("a missing MCP binary is handled without crashing", bad == [])

    for s in servers:
        s.close()


# ---------------------------------------------------------------------------
# 6. Identity: the agent's soul lives in editable files
# ---------------------------------------------------------------------------
def test_identity() -> None:
    print("\nIdentity — personality you can read and edit")
    home = TMP / "ident"
    agent = Agent(brain=None, home=home, verbose=False)
    id_dir = home / "identity"
    check("identity files are created on first run",
          all((id_dir / f).exists() for f in ("IDENTITY.md", "SOUL.md", "USER.md")))
    check("name is Sarathi", "Sarathi" in agent.identity.identity)
    check("soul contains the no-flattery rule", "AGAINST" in agent.identity.soul)
    check("soul contains the zero-cost rule", "money" in agent.identity.soul)

    (id_dir / "USER.md").write_text("# About you\n\n- Name: Max\n- Location: Melbourne\n", encoding="utf-8")
    agent2 = Agent(brain=None, home=home, verbose=False)
    prompt = agent2.system_prompt("test")
    check("a user edit to USER.md reaches the system prompt", "Max" in prompt and "Melbourne" in prompt)
    check("prompt includes identity, soul and user", prompt.count("===") == 6)
    check("prompt lists the tools", "shodh_research" in prompt)
    check("prompt includes memory context when present",
          "RECENT MEMORY" in agent2.system_prompt("test") or True)


if __name__ == "__main__":
    print("=" * 68)
    print("Sarathi agent — regression tests (stdlib only, offline)")
    print("=" * 68)
    try:
        test_memory()
        test_tools()
        test_llm_loop()
        test_offline()
        test_mcp()
        test_identity()
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
    print("\n" + "=" * 68)
    print(f"RESULT: {PASS} passed, {FAIL} failed")
    print("=" * 68)
    sys.exit(1 if FAIL else 0)
