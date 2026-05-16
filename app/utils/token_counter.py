"""Token counting utility."""
from typing import Optional


class TokenCounter:
    """Estimate token counts for text."""

    def __init__(self):
        self.chars_per_token = 4  # Approximate

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        if not text:
            return 0
        return len(text) // self.chars_per_token

    def estimate_messages_tokens(self, messages: list) -> int:
        """Estimate tokens for a list of messages."""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "")
            # Add overhead for role
            total += self.estimate_tokens(content) + len(role) // 4
        return total

    def truncate_to_limit(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token limit."""
        estimated = self.estimate_tokens(text)
        if estimated <= max_tokens:
            return text

        max_chars = max_tokens * self.chars_per_token
        return text[:max_chars] + "..."


# Global instance
token_counter = TokenCounter()