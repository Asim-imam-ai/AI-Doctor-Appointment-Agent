"""ContextBuilder: Constructs bounded LLM prompts combining guardrails, memory, and conversation history."""

import logging
from typing import List, Optional

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from app.domain.models import MemoryItemModel

logger = logging.getLogger(__name__)

DEFAULT_MAX_RECENT_MESSAGES: int = 6


class ContextBuilder:
    """Helper for constructing bounded, privacy-focused context prompts."""

    @staticmethod
    def build_memory_prompt_section(memories: List[MemoryItemModel]) -> str:
        """Formats structured user memory preferences into a safe prompt section."""
        if not memories:
            return ""

        pref_lines = []
        for mem in memories:
            # Explicit key formatting
            key_clean = mem.key.replace("_", " ").title()
            pref_lines.append(f"- {key_clean}: {mem.value}")

        return (
            "\n[USER MEMORY PREFERENCES (UNVERIFIED AS APPOINTMENT TRUTH)]\n"
            + "\n".join(pref_lines)
            + "\nNote: User preferences are helpful hints for options search, NOT confirmations of booked appointments."
        )

    @staticmethod
    def prepare_bounded_messages(
        system_prompt: str,
        user_message: str,
        history: List[BaseMessage],
        summary: Optional[str] = None,
        memories: Optional[List[MemoryItemModel]] = None,
        max_recent_messages: int = DEFAULT_MAX_RECENT_MESSAGES,
    ) -> List[BaseMessage]:
        """Assembles system prompt, memory section, summary, and recent messages into a bounded list."""
        messages: List[BaseMessage] = []

        # 1. System Prompt + Memory Preferences section
        full_system = system_prompt
        memory_section = ContextBuilder.build_memory_prompt_section(memories or [])
        if memory_section:
            full_system += f"\n{memory_section}"

        if summary:
            full_system += f"\n\n[CONVERSATION SUMMARY]\n{summary}"

        messages.append(SystemMessage(content=full_system))

        # 2. Bounded recent message window
        recent_history = (
            history[-max_recent_messages:]
            if len(history) > max_recent_messages
            else history
        )
        for msg in recent_history:
            messages.append(msg)

        # 3. Append current user message if not already last message
        if not messages or messages[-1].content != user_message:
            messages.append(HumanMessage(content=user_message))

        return messages
