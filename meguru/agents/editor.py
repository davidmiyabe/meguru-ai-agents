"""Editor agent that refines planner briefs into user-facing updates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Mapping

from .planning import PlannerBrief


@dataclass
class EditorRevision:
    """Represents a polished message from the editor."""

    chunks: List[str] = field(default_factory=list)


class Editor:
    """Agent that translates planner structure into an actionable update."""

    system_prompt = (
        "You are Meguru's Editor. Blend the planner's structure with the traveller's "
        "tone, highlighting how selected activities fit together."
    )
    prompt_version = "plan.editor.v1"

    def run(self, brief: PlannerBrief, context: Mapping[str, object]) -> EditorRevision:
        """Return an editor revision ready to surface in chat."""

        if not brief.highlights:
            return EditorRevision(chunks=[])

        lines: List[str] = []
        if brief.framing:
            lines.append(brief.framing + ".")

        if brief.highlights:
            bullet_list = "\n".join(f"• {item}" for item in brief.highlights)
            lines.append(bullet_list)

        lines.append("Shout if you want to swap anything—I'll remix in seconds.")
        return EditorRevision(chunks=lines)


__all__ = ["Editor", "EditorRevision"]

