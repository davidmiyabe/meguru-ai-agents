"""Agent responsible for translating intake data into a :class:`TripIntent`."""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from meguru.agents import DEFAULT_AGENT_MODEL, call_llm_and_validate, format_prompt_data
from meguru.schemas import TripIntent


class IntakeAgent:
    """Normalises raw intake information into a :class:`TripIntent`."""

    system_prompt = (
        "You are an expert travel planner capturing the intent for an upcoming trip. "
        "Only respond with a JSON object that matches the TripIntent schema."
    )
    prompt_version = "intake.v1"

    def __init__(
        self,
        *,
        model: Optional[str] = None,
        stop: Optional[Sequence[str]] = None,
    ) -> None:
        self.model = model or DEFAULT_AGENT_MODEL
        self.stop = stop

    def run(
        self,
        *,
        free_text: Optional[str] = None,
        wizard_fields: Optional[Dict[str, Any]] = None,
    ) -> TripIntent:
        """Return a structured :class:`TripIntent` from user-provided data."""

        if not free_text and not wizard_fields:
            raise ValueError("Either free_text or wizard_fields must be provided.")

        prompt_payload = {
            "free_text": free_text,
            "wizard_fields": wizard_fields or {},
        }

        prompt = (
            "Extract a complete TripIntent from the following intake information.\n"
            "Fill in sensible defaults where details are missing, keeping interests aligned\n"
            "to the traveller's requests.\n"
            "\n"
            "# Intake Data\n"
            f"{format_prompt_data(prompt_payload)}\n"
            "\n"
            "Ensure destination, dates, pace, interests, and any constraints are clearly captured."
        )

        return call_llm_and_validate(
            schema=TripIntent,
            prompt=prompt,
            system_prompt=self.system_prompt,
            prompt_version=self.prompt_version,
            model=self.model,
            stop=self.stop,
        )


__all__ = ["IntakeAgent"]
