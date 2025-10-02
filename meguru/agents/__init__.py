"""Shared utilities for Meguru's LLM-backed agents."""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from typing import Any, Optional, Sequence, Type, TypeVar

from pydantic import BaseModel, ValidationError

from meguru.core.llm import llm_json

T = TypeVar("T", bound=BaseModel)


DEFAULT_AGENT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


class AgentExecutionError(RuntimeError):
    """Raised when an agent cannot return a valid payload."""


def _json_default(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, set):
        return sorted(value)
    return value


def format_prompt_data(data: Any) -> str:
    """Render arbitrary python data for inclusion in an LLM prompt."""

    return json.dumps(data, indent=2, default=_json_default)


def call_llm_and_validate(
    *,
    schema: Type[T],
    prompt: str,
    system_prompt: str,
    prompt_version: str,
    model: Optional[str] = None,
    stop: Optional[Sequence[str]] = None,
) -> T:
    """Call the shared LLM helper and validate the JSON payload."""

    data = llm_json(
        prompt=prompt,
        system=system_prompt,
        model=model or DEFAULT_AGENT_MODEL,
        stop=stop,
        prompt_version=prompt_version,
    )
    try:
        return schema.model_validate(data)
    except ValidationError as exc:  # pragma: no cover - exercised in tests via failure path
        raise AgentExecutionError(
            f"LLM response could not be validated as {schema.__name__}: {exc}"
        ) from exc


from .clarifier import Clarifier, ClarifierPrompt
from .curator import Curator, CuratorDraft
from .editor import Editor, EditorRevision
from .intake import IntakeAgent
from .listener import Listener, ListenerResult
from .planner import PlannerAgent
from .planning import Planner, PlannerBrief
from .refiner import RefinerAgent
from .researcher import ResearcherAgent
from .stylist import Stylist, StyledResponse
from .summary import SummaryAgent
from .taste import TasteAgent

__all__ = [
    "AgentExecutionError",
    "DEFAULT_AGENT_MODEL",
    "Clarifier",
    "ClarifierPrompt",
    "Curator",
    "CuratorDraft",
    "Editor",
    "EditorRevision",
    "IntakeAgent",
    "Listener",
    "ListenerResult",
    "Planner",
    "PlannerAgent",
    "PlannerBrief",
    "RefinerAgent",
    "ResearcherAgent",
    "Stylist",
    "StyledResponse",
    "SummaryAgent",
    "TasteAgent",
    "call_llm_and_validate",
    "format_prompt_data",
]
