"""
Sarathi — the agent runtime.

    Sarathi Labs   the lab
    Sarathi        the AGENT       (this package: an always-available process with memory + tools)
    Shodh          the engine      (retrieval + reasoning over the corpus)
    Arthabodh      the deliverable (the report the agent produces)

An app waits for someone to visit it. Sarathi runs.
"""
from .loop import Agent, Turn, Step
from .memory import AgentMemory, Memory
from . import tools, identity

__version__ = "0.3.0"
__all__ = ["Agent", "Turn", "Step", "AgentMemory", "Memory", "tools", "identity"]
