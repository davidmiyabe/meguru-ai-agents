"""Listener agent that normalises user actions into planner context updates."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


_VIBE_OPTIONS = [
    "Nightlife",
    "Foodie adventures",
    "Culture & history",
    "Outdoors & nature",
    "Something eclectic",
]

_PACE_OPTIONS = ["Laid back", "Balanced", "All-out"]
_BUDGET_OPTIONS = ["Shoestring", "Moderate", "Splurge"]


_MOOD_KEYWORDS = {
    "burned_out": (
        "burned out",
        "burnt out",
        "burned-out",
        "burnt-out",
        "overwhelmed",
        "exhausted",
        "fried",
        "stressed",
        "drained",
    ),
    "celebration": (
        "celebrate",
        "celebration",
        "birthday",
        "anniversary",
        "promotion",
        "engagement",
        "honeymoon",
        "bachelorette",
        "bachelor party",
        "graduation",
    ),
    "peaceful": (
        "peaceful",
        "peace",
        "calm",
        "serene",
        "restful",
        "unwind",
        "relax",
        "recharge",
        "reset",
        "quiet",
    ),
}


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _extract_group_type(text: str) -> Optional[str]:
    lowered = _normalise(text)
    options = {
        "solo": "Just me",
        "alone": "Just me",
        "myself": "Just me",
        "partner": "Partner getaway",
        "spouse": "Partner getaway",
        "wife": "Partner getaway",
        "husband": "Partner getaway",
        "girlfriend": "Partner getaway",
        "boyfriend": "Partner getaway",
        "couple": "Partner getaway",
        "family": "Family crew",
        "kids": "Family crew",
        "parents": "Family crew",
        "friends": "Friends trip",
        "buddies": "Friends trip",
        "mates": "Friends trip",
        "cowork": "Workmates",
        "colleague": "Workmates",
        "team": "Workmates",
        "office": "Workmates",
    }
    for keyword, option in options.items():
        if keyword in lowered:
            return option
    return None


_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}


def _extract_group_size(text: str) -> Optional[int]:
    digits = re.findall(r"\d+", text)
    if digits:
        try:
            value = int(digits[0])
            if value > 0:
                return value
        except ValueError:
            pass

    lowered = _normalise(text)
    for word, value in _NUMBER_WORDS.items():
        if word in lowered:
            return value
    keyword_defaults = {"couple": 2, "pair": 2, "duo": 2, "solo": 1, "myself": 1}
    for keyword, value in keyword_defaults.items():
        if keyword in lowered:
            return value
    return None


def _coerce_positive_int(value: object) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, float) and value.is_integer():
        numeric = int(value)
        return numeric if numeric > 0 else None
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        try:
            numeric = int(cleaned)
        except ValueError:
            return None
        return numeric if numeric > 0 else None
    try:
        numeric = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return numeric if numeric > 0 else None


_VIBE_KEYWORDS = {
    "night": "Nightlife",
    "club": "Nightlife",
    "bar": "Nightlife",
    "food": "Foodie adventures",
    "eat": "Foodie adventures",
    "restaurant": "Foodie adventures",
    "culture": "Culture & history",
    "museum": "Culture & history",
    "history": "Culture & history",
    "outdoor": "Outdoors & nature",
    "hike": "Outdoors & nature",
    "nature": "Outdoors & nature",
    "forest": "Outdoors & nature",
    "eclectic": "Something eclectic",
    "art": "Something eclectic",
    "design": "Something eclectic",
}


def _extract_vibes(text: str) -> List[str]:
    lowered = _normalise(text)
    detected: List[str] = []
    for option in _VIBE_OPTIONS:
        if option.lower() in lowered:
            detected.append(option)
    for keyword, option in _VIBE_KEYWORDS.items():
        if keyword in lowered and option not in detected:
            detected.append(option)
    for chunk in re.split(r"[,/]| and ", lowered):
        chunk = chunk.strip()
        for option in _VIBE_OPTIONS:
            if chunk == option.lower() and option not in detected:
                detected.append(option)
    return detected


def _extract_mood(text: str) -> Optional[str]:
    lowered = _normalise(text)
    if not lowered:
        return None

    for mood, keywords in _MOOD_KEYWORDS.items():
        for keyword in keywords:
            if keyword in lowered:
                return mood
    return None


def _infer_travel_pace(text: str) -> Optional[str]:
    lowered = _normalise(text)
    laid_back_markers = ("laid back", "laid-back", "laidback")
    if any(token in lowered for token in laid_back_markers) or any(
        token in lowered for token in ("relax", "slow", "chill", "easy", "unhurried")
    ):
        return "Laid back"
    if any(token in lowered for token in ("balanced", "mix", "medium", "moderate")):
        return "Balanced"
    if any(token in lowered for token in ("packed", "full", "busy", "nonstop", "all out", "all-out")):
        return "All-out"
    return None


def _infer_budget(text: str) -> Optional[str]:
    lowered = _normalise(text)
    if any(token in lowered for token in ("cheap", "budget", "shoestring", "tight", "save")):
        return "Shoestring"
    if any(token in lowered for token in ("mid", "moderate", "reasonable", "comfortable", "middle")):
        return "Moderate"
    if any(token in lowered for token in ("lux", "splurge", "premium", "fancy", "high end", "high-end")):
        return "Splurge"
    return None


_MONTH_NAMES = [
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
]


def _extract_timing(text: str) -> Optional[str]:
    lowered = _normalise(text)
    if any(month in lowered for month in _MONTH_NAMES):
        return text.strip()
    if re.search(r"\d{4}", lowered) or re.search(r"\d{1,2}/\d{1,2}", lowered):
        return text.strip()
    if any(token in lowered for token in ("week", "weekend", "month", "summer", "winter")):
        return text.strip()
    return None


_DESTINATION_STOP_WORDS = {
    "in",
    "for",
    "with",
    "during",
    "over",
    "around",
    "through",
    "while",
    "when",
    "because",
    "since",
    "after",
    "before",
    "on",
    "at",
    "by",
    "from",
    "this",
    "next",
    "the",
    "a",
    "an",
    "my",
    "our",
    "his",
    "her",
    "their",
}


def _guess_destination(text: str) -> Optional[str]:
    stripped = text.strip()
    if not stripped:
        return None

    pattern = re.compile(r"(?:to|in|around|for)\s+([A-Za-z][A-Za-z\s\-']{2,})", re.IGNORECASE)
    match = pattern.search(stripped)
    if match:
        candidate = match.group(1).strip()
        tokens: List[str] = []
        for raw_token in candidate.split():
            cleaned = raw_token.strip(" ,.;:!?")
            if not cleaned:
                continue
            lowered = cleaned.lower()
            if lowered in _DESTINATION_STOP_WORDS and tokens:
                break
            tokens.append(cleaned)
        candidate = " ".join(tokens).strip("- ,")
        if candidate:
            return candidate.title()

    tokens = stripped.split()
    if 1 <= len(tokens) <= 4:
        return stripped.title()
    return None


@dataclass
class ListenerResult:
    """Structured response describing the outcome of a listener pass."""

    action_type: str
    user_message: str
    context_updates: Dict[str, Any] = field(default_factory=dict)
    missing_context: List[str] = field(default_factory=list)
    resolved_fields: List[str] = field(default_factory=list)
    trigger_planning: bool = False


class Listener:
    """Agent that listens to user actions and extracts planning context."""

    system_prompt = (
        "You are Meguru's Listener. Interpret every traveller action—chat messages, "
        "likes, saves—and translate them into structured updates for downstream "
        "agents. Recognise destinations, timing clues, group make-up, vibes, pace, "
        "and budget signals. Flag missing context so the Clarifier can follow up."
    )
    prompt_version = "plan.listener.v1"

    _required_fields = ["destination", "timing", "vibe", "travel_pace", "budget", "group"]

    def run(
        self,
        *,
        action_json: str,
        context: Mapping[str, Any],
        pending_fields: Sequence[str] | None = None,
    ) -> ListenerResult:
        try:
            payload = json.loads(action_json)
        except json.JSONDecodeError:
            payload = {"type": "message", "text": action_json}

        action_type = str(payload.get("type") or "message")
        context_updates: Dict[str, Any] = {}
        resolved_fields: List[str] = []
        user_message = ""
        trigger_planning = False

        pending = list(pending_fields or [])

        if action_type == "message":
            text = str(payload.get("text", "")).strip()
            user_message = text or "Sharing more trip details."
            if text:
                context_updates["notes_append"] = text

            destination = _guess_destination(text)
            if destination:
                context_updates["destination"] = destination

            timing = _extract_timing(text)
            if timing:
                context_updates["timing_note"] = timing

            vibes = _extract_vibes(text)
            if vibes:
                context_updates.setdefault("vibe_add", []).extend(vibes)

            pace = _infer_travel_pace(text)
            if pace:
                context_updates["travel_pace"] = pace

            budget = _infer_budget(text)
            if budget:
                context_updates["budget"] = budget

            group_type = _extract_group_type(text)
            if group_type:
                context_updates["group_type"] = group_type

            group_size = _extract_group_size(text)
            if group_size:
                context_updates["group_size"] = group_size

            mood = _extract_mood(text)
            if mood:
                context_updates["mood"] = mood

        elif action_type in {"like_activity", "save_activity", "unlike_activity", "unsave_activity"}:
            card = payload.get("card") if isinstance(payload.get("card"), dict) else {}
            card_title = str(card.get("title") or card.get("id") or "this experience")
            card_id = str(card.get("id") or card_title)
            catalog_update: Dict[str, Any] = {card_id: card}

            if action_type == "like_activity":
                user_message = f"❤️ Liked {card_title}"
                context_updates.setdefault("liked_cards_add", []).append(card_id)
                trigger_planning = True
            elif action_type == "save_activity":
                user_message = f"🔖 Saved {card_title}"
                context_updates.setdefault("saved_cards_add", []).append(card_id)
                trigger_planning = True
            elif action_type == "unlike_activity":
                user_message = f"Removed like from {card_title}"
                context_updates.setdefault("liked_cards_remove", []).append(card_id)
            else:
                user_message = f"Removed {card_title} from saved picks"
                context_updates.setdefault("saved_cards_remove", []).append(card_id)

            context_updates.setdefault("activity_catalog", {}).update(catalog_update)
        else:
            user_message = "Noted."

        merged_context = self._merge_context(context, context_updates)

        for field in pending:
            if self._has_field(merged_context, field):
                resolved_fields.append(field)

        missing_context = self._detect_missing_fields(merged_context, pending, resolved_fields)

        return ListenerResult(
            action_type=action_type,
            user_message=user_message,
            context_updates=context_updates,
            missing_context=missing_context,
            resolved_fields=resolved_fields,
            trigger_planning=trigger_planning,
        )

    def _merge_context(
        self, context: Mapping[str, Any], updates: Mapping[str, Any]
    ) -> Dict[str, Any]:
        merged: Dict[str, Any] = dict(context)
        merged.setdefault("notes", "")
        merged.setdefault("vibe", [])
        merged.setdefault("timing_note", context.get("timing_note"))

        if "notes_append" in updates and updates["notes_append"]:
            existing = str(merged.get("notes", "")).strip()
            addition = str(updates["notes_append"]).strip()
            merged["notes"] = f"{existing}\n{addition}".strip() if existing else addition

        if "destination" in updates and updates["destination"]:
            merged["destination"] = updates["destination"]
        if "timing_note" in updates and updates["timing_note"]:
            merged["timing_note"] = updates["timing_note"]
        if "travel_pace" in updates and updates["travel_pace"]:
            merged["travel_pace"] = updates["travel_pace"]
        if "budget" in updates and updates["budget"]:
            merged["budget"] = updates["budget"]
        if "group_type" in updates and updates["group_type"]:
            merged["group_type"] = updates["group_type"]
        if "group_size" in updates and updates["group_size"]:
            merged["group_size"] = updates["group_size"]
        if "mood" in updates and updates["mood"]:
            merged["mood"] = updates["mood"]

        vibes: Iterable[str] = updates.get("vibe_add") or []
        if vibes:
            current = {str(item) for item in merged.get("vibe", []) if isinstance(item, str)}
            for vibe in vibes:
                if vibe:
                    current.add(str(vibe))
            merged["vibe"] = sorted(current)

        return merged

    def _has_field(self, context: Mapping[str, Any], field: str) -> bool:
        if field == "destination":
            return bool(str(context.get("destination", "")).strip())
        if field == "timing":
            if context.get("start_date") and context.get("end_date"):
                return True
            if context.get("flexible_months"):
                return True
            return bool(str(context.get("timing_note", "")).strip())
        if field == "vibe":
            vibes = context.get("vibe") or []
            return bool(vibes)
        if field == "travel_pace":
            return str(context.get("travel_pace", "")).strip() in _PACE_OPTIONS
        if field == "budget":
            return str(context.get("budget", "")).strip() in _BUDGET_OPTIONS
        if field == "group":
            group_type = str(context.get("group_type", "")).strip()
            if group_type:
                return True
            return _coerce_positive_int(context.get("group_size")) is not None
        return False

    def _detect_missing_fields(
        self,
        context: Mapping[str, Any],
        pending: Sequence[str],
        resolved_fields: Sequence[str],
    ) -> List[str]:
        remaining = [field for field in pending if field not in resolved_fields]
        if remaining:
            return list(dict.fromkeys(remaining))

        for field in self._required_fields:
            if not self._has_field(context, field):
                return [field]
        return []


__all__ = ["Listener", "ListenerResult"]

