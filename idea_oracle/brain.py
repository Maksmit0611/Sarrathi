"""
brain.py — the pluggable "brain" for Arthabodh (Sarathi Labs).

Design goal: ZERO COST BY DEFAULT, ZERO DEPENDENCIES.
Every provider below has a genuinely free tier and speaks the OpenAI-compatible
Chat Completions API, so one adapter works for all of them and we only need
Python's standard library (urllib) - no `pip install openai` required.

Fallback ladder:
  1. Whichever provider has an API key in the environment (or IDEA_ORACLE_BRAIN forces one)
  2. Local Ollama if it is running (100% free, offline)
  3. OfflineBrain - a deterministic, template-based synthesiser that needs no LLM at all.

Mode 3 matters: it means the app always produces a useful, evidence-grounded
report even with no keys, no internet and no money. The LLM only makes the
prose better - it is never required for the app to function.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

# ---------------------------------------------------------------------------
# Free provider registry. Add your key to .env / environment to activate one.
# Free-tier facts verified Oct 2026 - limits change often; check each provider.
# ---------------------------------------------------------------------------
PROVIDERS: dict[str, dict] = {
    "groq": {
        "label": "Groq (free tier, very fast)",
        "base_url": "https://api.groq.com/openai/v1",
        "key_env": "GROQ_API_KEY",
        "model": "openai/gpt-oss-120b",
        "fallback_models": ["openai/gpt-oss-20b", "qwen/qwen3.6-27b"],
        "signup": "https://console.groq.com/keys",
    },
    "gemini": {
        "label": "Google Gemini (free tier, no card)",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "key_env": "GEMINI_API_KEY",
        "model": "gemini-2.5-flash",
        "fallback_models": ["gemini-2.5-flash-lite"],
        "signup": "https://aistudio.google.com/apikey",
    },
    "openrouter": {
        "label": "OpenRouter (many :free models, one key)",
        "base_url": "https://openrouter.ai/api/v1",
        "key_env": "OPENROUTER_API_KEY",
        "model": "deepseek/deepseek-chat-v3.1:free",
        "fallback_models": ["meta-llama/llama-3.3-70b-instruct:free", "openrouter/free"],
        "signup": "https://openrouter.ai/keys",
    },
    "nvidia": {
        "label": "NVIDIA NIM (120+ open models, free prototyping)",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "key_env": "NVIDIA_API_KEY",
        "model": "meta/llama-3.3-70b-instruct",
        "fallback_models": [],
        "signup": "https://build.nvidia.com",
    },
    "mistral": {
        "label": "Mistral La Plateforme (free experiment tier)",
        "base_url": "https://api.mistral.ai/v1",
        "key_env": "MISTRAL_API_KEY",
        "model": "mistral-small-latest",
        "fallback_models": [],
        "signup": "https://console.mistral.ai",
    },
    "ollama": {
        "label": "Ollama (100% local & free, no key)",
        "base_url": "http://localhost:11434/v1",
        "key_env": None,  # no key needed
        "model": "llama3.1",
        "fallback_models": ["qwen2.5", "phi4", "gemma3"],
        "signup": "https://ollama.com/download",
    },
}


class BrainError(RuntimeError):
    pass


class Brain:
    """OpenAI-compatible chat client with free-provider auto-detection."""

    def __init__(self, provider: str | None = None, model: str | None = None, timeout: int = 90):
        self.timeout = timeout
        self.provider_name = provider or self._autodetect()
        if self.provider_name is None:
            raise BrainError(
                "No brain found. Set one of: "
                + ", ".join(p["key_env"] for p in PROVIDERS.values() if p["key_env"])
                + " — or run Ollama locally, or use OfflineBrain()."
            )
        p = PROVIDERS[self.provider_name]
        self.label = p["label"]
        self.base_url = p["base_url"].rstrip("/")
        self.model = model or p["model"]
        self._fallback_models = [m for m in p["fallback_models"] if m != self.model]
        key_env = p["key_env"]
        self.api_key = os.environ.get(key_env, "") if key_env else "ollama"

    @staticmethod
    def _autodetect() -> str | None:
        forced = os.environ.get("IDEA_ORACLE_BRAIN", "").strip().lower()
        if forced:
            return forced if forced in PROVIDERS else None
        # Prefer the fastest / most generous free tiers first
        for name in ("groq", "gemini", "openrouter", "nvidia", "mistral"):
            env = PROVIDERS[name]["key_env"]
            if env and os.environ.get(env):
                return name
        # Last resort: a local Ollama instance
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=2):
                return "ollama"
        except Exception:
            return None

    # -- core call ---------------------------------------------------------
    def chat(self, system: str, user: str, temperature: float = 0.4, max_tokens: int = 2200) -> str:
        """Send one system+user turn and return the assistant text."""
        models = [self.model] + self._fallback_models
        last_error: Exception | None = None
        for model in models:
            try:
                return self._chat_once(model, system, user, temperature, max_tokens)
            except Exception as exc:  # noqa: BLE001 - try next model on any provider error
                last_error = exc
        raise BrainError(f"All models failed on {self.provider_name}. Last error: {last_error}")

    def chat_tools(self, messages: list[dict], tools: list[dict], temperature: float = 0.3,
                   max_tokens: int = 2000) -> dict:
        """
        Tool-calling turn: returns the raw assistant message, which may contain
        `tool_calls`. This is what turns a chat model into an agent - the model
        chooses a tool, we run it, and we feed the result back in.

        Providers differ in small ways; this normalises them into one shape:
            {"role": "assistant", "content": str, "tool_calls": [{"id", "function": {"name", "arguments"}}]}
        """
        last_error: Exception | None = None
        for model in [self.model] + self._fallback_models:
            try:
                return self._tools_once(model, messages, tools, temperature, max_tokens)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
        raise BrainError(f"Tool calling failed on {self.provider_name}. Last error: {last_error}")

    def _tools_once(self, model: str, messages: list[dict], tools: list[dict],
                    temperature: float, max_tokens: int) -> dict:
        payload: dict = {"model": model, "messages": messages, "temperature": temperature,
                         "max_tokens": max_tokens}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://localhost/sarathi-labs",
            "X-Title": "Sarathi (Sarathi Labs)",
        }
        req = urllib.request.Request(f"{self.base_url}/chat/completions",
                                     data=json.dumps(payload).encode("utf-8"),
                                     headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        msg = data["choices"][0]["message"]
        out: dict = {"role": "assistant", "content": msg.get("content") or ""}
        calls = msg.get("tool_calls") or []
        norm = []
        for i, c in enumerate(calls):
            fn = c.get("function", {})
            args = fn.get("arguments", "{}")
            if isinstance(args, dict):                     # some providers return an object
                args = json.dumps(args)
            norm.append({"id": c.get("id") or f"call_{i}", "type": "function",
                         "function": {"name": fn.get("name", ""), "arguments": args or "{}"}})
        if norm:
            out["tool_calls"] = norm
        return out

    def _chat_once(self, model: str, system: str, user: str, temperature: float, max_tokens: int) -> str:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            # OpenRouter asks for these; harmless elsewhere.
            "HTTP-Referer": "https://localhost/sarathi-labs",
            "X-Title": "Arthabodh (Sarathi Labs)",
        }
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]

    def __repr__(self) -> str:
        return f"<Brain {self.provider_name}:{self.model}>"


class OfflineBrain:
    """
    No-LLM synthesiser. Deterministic, free forever, works with no internet.

    This is not a fake LLM - it composes the report from retrieved evidence
    using rules and templates. The output is less fluent than an LLM's but the
    substance (retrieved cases, cultural scores, risk flags) is identical,
    because it is the same evidence the LLM receives.
    """

    label = "Offline (no LLM - rule-based synthesis)"
    provider_name = "offline"
    model = "rules-v1"

    def chat(self, system: str, user: str, temperature: float = 0.4, max_tokens: int = 2200) -> str:
        raise BrainError(
            "OfflineBrain cannot generate free-form text. Use IdeaOracle.analyze(), which builds "
            "the report from evidence directly - or run the Sarathi agent, whose loop routes to "
            "tools without a model."
        )

    def chat_tools(self, messages: list[dict], tools: list[dict], **kw) -> dict:
        raise BrainError("OfflineBrain has no tool calling. The Sarathi agent loop handles this.")


def get_brain(prefer_offline: bool = False):
    """Return the best available brain, or OfflineBrain if nothing is configured."""
    if prefer_offline:
        return OfflineBrain()
    try:
        return Brain()
    except BrainError:
        return OfflineBrain()


def describe_providers() -> str:
    lines = ["Free brains available (add a key to your environment to switch one on):", ""]
    for name, p in PROVIDERS.items():
        env = p["key_env"] or "(no key needed)"
        state = "ACTIVE" if (p["key_env"] and os.environ.get(p["key_env"])) else "not configured"
        lines.append(f"  {name:<11} {p['label']}")
        lines.append(f"              key env: {env:<22} status: {state}")
        lines.append(f"              signup : {p['signup']}")
        lines.append(f"              model  : {p['model']}")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    print(describe_providers())
    b = get_brain()
    print("Selected brain:", b.label)
