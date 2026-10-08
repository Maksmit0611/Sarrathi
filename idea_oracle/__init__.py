"""
Arthabodh — a $0, dependency-free business-idea research agent by Sarathi Labs.

    Sarathi Labs   the lab
    Arthabodh      the product  (this package's orchestration)
    Shodh          the retrieval + reasoning engine inside it

The Python package is imported as `idea_oracle` — a deliberate choice to keep
imports stable across the rename. See docs/BRAND.md.
"""
from .agent import IdeaOracle, parse_idea, risk_flags
from .brain import get_brain, Brain, OfflineBrain, describe_providers
from .retrievers import KnowledgeBase

__version__ = "0.2.0"

# Branding: Arthabodh is the product name. IdeaOracle remains as the original
# class name so existing code keeps working.
Arthabodh = IdeaOracle

__all__ = ["Arthabodh", "IdeaOracle", "parse_idea", "risk_flags", "get_brain", "Brain",
           "OfflineBrain", "describe_providers", "KnowledgeBase"]
