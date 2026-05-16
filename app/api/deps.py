"""API dependencies."""
from fastapi import Depends
from typing import Optional


async def get_current_user(user: Optional[dict] = None) -> Optional[dict]:
    """Get current user from request."""
    return user


async def get_optional_user(user: Optional[dict] = None) -> Optional[dict]:
    """Get optional user."""
    return user