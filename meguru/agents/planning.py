"""Planner agent that assembles beats from liked and saved activities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Mapping


@dataclass
class PlannerBrief:
    """Summary of traveller-selected activities for itinerary refinement."""

    highlights: List[str] = field(default_factory=list)
    framing: str | None = None


class Planner:
    """Agent that proposes structure using traveller-curated activities."""

    system_prompt = (
        "You are Meguru's Planner. Based on liked or saved activities, suggest how they "
        "could sequence across a day, grouping by vibe or neighbourhood."
    )
    prompt_version = "plan.planner.v1"

    def run(self, activities: Iterable[Mapping[str, str]], destination: str | None = None) -> PlannerBrief:
        """Return a lightweight plan suggestion referencing selected activities."""

        highlights: List[str] = []
        for entry in activities:
            title = entry.get("title") or entry.get("id") or "Experience"
            category = entry.get("category")
            if category:
                highlights.append(f"{title} • {category}")
            else:
                highlights.append(title)

        if not highlights:
            return PlannerBrief(highlights=[], framing=None)

        framing = "Stacking these picks into a single flow" if len(highlights) > 1 else "Locking this gem in"
        if destination:
            framing += f" for {destination}"

        return PlannerBrief(highlights=highlights, framing=framing)


__all__ = ["Planner", "PlannerBrief"]

