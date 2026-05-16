"""Model routing logic - intelligent routing based on query type."""
import re
from typing import Optional, List, Dict
from dataclasses import dataclass

from app.config import settings
from app.logging_config import log


@dataclass
class RouteRule:
    """Route rule for model selection."""
    patterns: List[str]
    model: str
    description: str
    priority: int = 0


class ModelRouter:
    """Intelligent model routing based on query content."""

    def __init__(self):
        self.rules: List[RouteRule] = self._init_rules()

    def _init_rules(self) -> List[RouteRule]:
        """Initialize routing rules."""
        return [
            # Coding/Programming - highest priority
            RouteRule(
                patterns=[
                    r"\bcode\b", r"\bprogramming\b", r"\bfunction\b",
                    r"\bclass\b", r"\bdef\b", r"\bimport\b",
                    r"\bvar\b", r"\blet\b", r"\bconst\b",
                    r"\bif\b.*\bthen\b", r"\belse\b", r"\bswitch\b",
                    r"```", r"print\(", r"console\.log",
                    r"def\s+\w+\(", r"class\s+\w+",
                    r"function\s+\w+\(", r"public\s+(static\s+)?void",
                    r"import\s+", r"#include", r"package\s+",
                    r"implement", r"interface", r"abstract"
                ],
                model="deepseek-coder",
                description="Coding and programming tasks",
                priority=10
            ),
            # Reasoning/Math
            RouteRule(
                patterns=[
                    r"\bsolve\b", r"\bcalculate\b", r"\bmath\b",
                    r"\bprove\b", r"\breasoning\b", r"\blogic\b",
                    r"\balgorithm\b", r"\btheorem\b", r"\bequation\b",
                    r"\bproof\b", r"\bderive\b", r"\boptimize\b",
                    r"\bcompare\b", r"\banalyze\b", r"\bevaluate\b",
                    r"\bstep\s+by\s+step", r"\bexplain\s+why\b"
                ],
                model="qwen2.5",
                description="Reasoning and mathematical tasks",
                priority=8
            ),
            # Creative/Writing
            RouteRule(
                patterns=[
                    r"\bwrite\b", r"\bstory\b", r"\bpoem\b",
                    r"\bcreative\b", r"\bnarrative\b", r"\bessay\b",
                    r"\bblog\b", r"\barticle\b", r"\bcompose\b",
                    r"\bsummarize\b", r"\breview\b", r"\bexplain\b",
                    r"\bdescribe\b", r"\bimagine\b"
                ],
                model="llama3.2",
                description="Creative writing tasks",
                priority=5
            ),
            # General chat - lowest priority
            RouteRule(
                patterns=[],
                model=settings.default_model,
                description="General conversation",
                priority=1
            )
        ]

    def route(self, query: str, user_model_preference: Optional[str] = None) -> str:
        """
        Route a query to the appropriate model.

        Args:
            query: User query
            user_model_preference: User's preferred model (if any)

        Returns:
            Model name to use
        """
        # If user has a preference, use it
        if user_model_preference:
            log.info(f"Using user preference: {user_model_preference}")
            return user_model_preference

        # Check query against rules
        query_lower = query.lower()

        for rule in sorted(self.rules, key=lambda r: r.priority, reverse=True):
            if not rule.patterns:  # Skip default rule
                continue

            matches = sum(
                1 for pattern in rule.patterns
                if re.search(pattern, query_lower, re.IGNORECASE)
            )

            if matches >= 2:  # Require at least 2 pattern matches
                log.info(f"Routed to {rule.model} based on {matches} patterns")
                return rule.model

        # Default to configured default model
        default = settings.default_model
        log.info(f"Using default model: {default}")
        return default

    def get_model_description(self, model: str) -> str:
        """Get description of a model's capabilities."""
        descriptions = {
            "deepseek-coder": "Specialized in code generation, debugging, and programming tasks",
            "llama3.2": "General purpose model for conversation and text tasks",
            "qwen2.5": "Strong in reasoning, math, and analytical tasks"
        }
        return descriptions.get(model, "General purpose model")

    def add_custom_rule(self, patterns: List[str], model: str, description: str, priority: int = 5):
        """Add a custom routing rule."""
        rule = RouteRule(
            patterns=patterns,
            model=model,
            description=description,
            priority=priority
        )
        self.rules.append(rule)
        log.info(f"Added custom rule: {description} -> {model}")


# Global router instance
model_router = ModelRouter()