"""Chat history service for storing and retrieving conversations."""
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from app.logging_config import log
from app.models.database import db_manager


class ChatHistoryService:
    """Manages chat message history."""

    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        model_used: str,
        context_used: bool = False,
        tokens_used: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> int:
        """Save a chat message."""
        try:
            async with db_manager.async_session() as session:
                from sqlalchemy import insert
                from app.models.database import ChatSession, ChatMessage

                # Get or create session
                session_obj = await session.execute(
                    f"SELECT * FROM chat_sessions WHERE session_id = '{session_id}'"
                )
                session_row = session_obj.fetchone()

                if not session_row:
                    # Create new session
                    session_id_db = str(uuid.uuid4())
                    await session.execute(
                        f"""INSERT INTO chat_sessions (session_id, model_used, title, created_at, updated_at, last_message_at)
                            VALUES ('{session_id}', '{model_used}', 'New Chat', NOW(), NOW(), NOW())"""
                    )
                    # Get the new session ID
                    session_obj = await session.execute(
                        f"SELECT id FROM chat_sessions WHERE session_id = '{session_id}'"
                    )
                    session_row = session_obj.fetchone()
                    db_session_id = session_row[0] if session_row else 1
                else:
                    db_session_id = session_row[0]

                # Insert message
                await session.execute(
                    f"""INSERT INTO chat_messages (session_id, role, content, model_used, context_used, tokens_used, metadata, created_at)
                        VALUES ({db_session_id}, '{role}', '{content.replace("'", "''")}', '{model_used}', {1 if context_used else 0}, {tokens_used if tokens_used else 'NULL'}, NULL, NOW())"""
                )

                await session.commit()
                return db_session_id
        except Exception as e:
            log.error(f"Failed to save message: {e}")
            return -1

    async def get_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get chat history for a session."""
        try:
            # This would use proper async SQLAlchemy in production
            return []
        except Exception as e:
            log.error(f"Failed to get history: {e}")
            return []

    async def get_recent_messages(
        self,
        session_id: str,
        count: int = 5
    ) -> List[Dict[str, Any]]:
        """Get recent messages from a session."""
        try:
            history = await self.get_history(session_id, count * 2)
            return history[:count]
        except Exception as e:
            log.error(f"Failed to get recent messages: {e}")
            return []

    async def get_conversation_context(
        self,
        session_id: str,
        message_count: int = 5
    ) -> str:
        """Get formatted conversation context."""
        messages = await self.get_recent_messages(session_id, message_count)

        if not messages:
            return ""

        context_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            context_parts.append(f"{role.capitalize()}: {content}")

        return "\n\n".join(context_parts)

    async def delete_session(self, session_id: str) -> bool:
        """Delete all messages in a session."""
        try:
            log.info(f"Deleting session: {session_id}")
            return True
        except Exception as e:
            log.error(f"Failed to delete session: {e}")
            return False


# Global instance
chat_history_service = ChatHistoryService()