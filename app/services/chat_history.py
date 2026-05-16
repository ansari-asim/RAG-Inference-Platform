"""Chat history service for storing and retrieving conversations."""
from typing import List, Optional
from datetime import datetime, timedelta
import json

from app.models.database import ChatMessage, db_manager
from app.logging_config import log


class ChatHistoryService:
    """Manages chat message history."""

    async def save_message(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        model_used: str,
        context_used: bool = False,
        metadata: Optional[dict] = None
    ) -> int:
        """
        Save a chat message pair to history.

        Args:
            session_id: Session identifier
            user_message: User's message
            assistant_message: Assistant's response
            model_used: Model used for generation
            context_used: Whether context was used
            metadata: Additional metadata

        Returns:
            Message ID
        """
        try:
            async with db_manager.async_session() as session:
                message = ChatMessage(
                    session_id=session_id,
                    user_message=user_message,
                    assistant_message=assistant_message,
                    model_used=model_used,
                    context_used=1 if context_used else 0,
                    metadata=metadata
                )
                session.add(message)
                await session.commit()

                message_id = message.id
                log.info(f"Saved chat message to session {session_id}")
                return message_id

        except Exception as e:
            log.error(f"Failed to save chat message: {e}")
            return -1

    async def get_history(
        self,
        session_id: str,
        limit: int = 50,
        before_id: Optional[int] = None
    ) -> List[dict]:
        """
        Get chat history for a session.

        Args:
            session_id: Session identifier
            limit: Maximum messages to return
            before_id: Get messages before this ID (for pagination)

        Returns:
            List of message dicts
        """
        try:
            async with db_manager.async_session() as session:
                from sqlalchemy import select, desc

                query = select(ChatMessage).where(
                    ChatMessage.session_id == session_id
                ).order_by(desc(ChatMessage.created_at))

                if before_id:
                    query = query.where(ChatMessage.id < before_id)

                query = query.limit(limit)

                result = await session.execute(query)
                messages = result.scalars().all()

                # Format messages
                history = []
                for msg in reversed(messages):
                    history.append({
                        'id': msg.id,
                        'session_id': msg.session_id,
                        'user_message': msg.user_message,
                        'assistant_message': msg.assistant_message,
                        'model_used': msg.model_used,
                        'created_at': msg.created_at.isoformat() if msg.created_at else None,
                        'context_used': bool(msg.context_used),
                        'metadata': msg.metadata
                    })

                return history

        except Exception as e:
            log.error(f"Failed to get chat history: {e}")
            return []

    async def get_recent_messages(
        self,
        session_id: str,
        count: int = 10
    ) -> List[dict]:
        """
        Get the most recent messages from a session.

        Args:
            session_id: Session identifier
            count: Number of message pairs to get

        Returns:
            List of recent messages
        """
        messages = await self.get_history(session_id, limit=count * 2)
        return messages[:count]

    async def get_conversation_context(
        self,
        session_id: str,
        message_count: int = 5
    ) -> str:
        """
        Get formatted conversation context for prompt augmentation.

        Args:
            session_id: Session identifier
            message_count: Number of recent messages to include

        Returns:
            Formatted conversation string
        """
        messages = await self.get_recent_messages(session_id, message_count)

        if not messages:
            return ""

        context_parts = []
        for msg in messages:
            context_parts.append(f"User: {msg['user_message']}")
            context_parts.append(f"Assistant: {msg['assistant_message']}")

        return "\n\n".join(context_parts)

    async def delete_session(self, session_id: str) -> bool:
        """Delete all messages in a session."""
        try:
            async with db_manager.async_session() as session:
                from sqlalchemy import delete

                await session.execute(
                    delete(ChatMessage).where(ChatMessage.session_id == session_id)
                )
                await session.commit()

            log.info(f"Deleted session {session_id}")
            return True

        except Exception as e:
            log.error(f"Failed to delete session: {e}")
            return False

    async def search_history(
        self,
        session_id: Optional[str] = None,
        query: str = None,
        limit: int = 20
    ) -> List[dict]:
        """Search chat history."""
        try:
            async with db_manager.async_session() as session:
                from sqlalchemy import select, or_

                q = select(ChatMessage)

                if session_id:
                    q = q.where(ChatMessage.session_id == session_id)

                if query:
                    search_pattern = f"%{query}%"
                    q = q.where(
                        or_(
                            ChatMessage.user_message.ilike(search_pattern),
                            ChatMessage.assistant_message.ilike(search_pattern)
                        )
                    )

                q = q.order_by(ChatMessage.created_at.desc()).limit(limit)

                result = await session.execute(q)
                messages = result.scalars().all()

                return [{
                    'id': msg.id,
                    'session_id': msg.session_id,
                    'user_message': msg.user_message,
                    'assistant_message': msg.assistant_message,
                    'created_at': msg.created_at.isoformat() if msg.created_at else None
                } for msg in messages]

        except Exception as e:
            log.error(f"Failed to search history: {e}")
            return []


# Global instance
chat_history_service = ChatHistoryService()