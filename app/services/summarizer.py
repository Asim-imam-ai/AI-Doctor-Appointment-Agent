"""Summarizer: Summarizes conversation history preserving appointment context without hallucinating state."""

import logging
from typing import List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM_PROMPT = """You are a concise conversation summarizer for a doctor appointment assistant.
Summarize the key appointment context from the conversation history provided.

RULES:
1. Retain user preferences (doctor name, specialty, preferred times, location).
2. Retain current appointment workflow state (e.g. pending doctor search, selected doctor/slot).
3. DO NOT include medical diagnoses, symptoms, treatments, or sensitive health data.
4. DO NOT claim an appointment is CONFIRMED unless backed by explicit booking confirmation.
5. Keep the summary under 150 words.
"""


def summarize_conversation(
    messages: List[BaseMessage],
    llm: Optional[BaseChatModel] = None,
    existing_summary: Optional[str] = None,
) -> str:
    """Summarizes conversation messages safely using LLM or deterministic fallback."""
    if not messages:
        return existing_summary or ""

    # Form text representation of messages
    formatted_msgs = []
    if existing_summary:
        formatted_msgs.append(f"Previous Summary: {existing_summary}")

    for m in messages:
        role = "User" if isinstance(m, HumanMessage) else "Assistant"
        formatted_msgs.append(f"{role}: {m.content}")

    chat_history_text = "\n".join(formatted_msgs)

    if llm is None:
        try:
            from langchain_openai import ChatOpenAI

            from app.core.config import settings

            llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY or "dummy-key",
                temperature=0.0,
            )
        except Exception as e:
            logger.warning(
                f"LLM init failed for summarization, fallback to simple summary: {e}"
            )
            return (
                f"{existing_summary or ''} User was looking for doctor appointment options."
            ).strip()

    try:
        response = llm.invoke(
            [
                SystemMessage(content=SUMMARY_SYSTEM_PROMPT),
                HumanMessage(
                    content=f"Summarize this conversation:\n{chat_history_text}"
                ),
            ]
        )
        return str(response.content).strip()
    except Exception as e:
        logger.warning(f"LLM invocation failed during summarization: {e}")
        return (
            f"{existing_summary or ''} User engaged in appointment search workflow."
        ).strip()
