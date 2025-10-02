"""UI helpers for the cinematic trip planning journey."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple, TypedDict

import streamlit as st

from meguru.schemas import TripIntent
from meguru.workflows.trip_pipeline import run_trip_pipeline

_WIZARD_KEY = "_plan_wizard_state"
_TRIP_INTENT_KEY = "trip_intent"
_ITINERARY_KEY = "itinerary"
_PIPELINE_ERROR_KEY = "pipeline_error"

_GROUP_TYPES = [
    "Just me",
    "Partner getaway",
    "Family crew",
    "Friends trip",
    "Workmates",
]
_PACE_OPTIONS = ["Laid back", "Balanced", "All-out"]
_BUDGET_OPTIONS = ["Shoestring", "Moderate", "Splurge"]
_VIBE_OPTIONS = [
    "Nightlife",
    "Foodie adventures",
    "Culture & history",
    "Outdoors & nature",
    "Something eclectic",
]


class _ExperienceCard(TypedDict):
    """Static representation of an experience suggestion card."""

    id: str
    title: str
    description: str
    category: str
    image_url: str
    location_hint: str


_EXPERIENCE_CARDS: List[_ExperienceCard] = [
    {
        "id": "neon_bazaar",
        "title": "Neon Night Bazaar Crawl",
        "description": "Slide into hidden bars, late-night bites, and rooftop lounges with a local host.",
        "category": "Nightlife",
        "image_url": "https://images.unsplash.com/photo-1504805572947-34fad45aed93?auto=format&fit=crop&w=1200&q=80",
        "location_hint": "Perfect for electric evenings and skyline views.",
    },
    {
        "id": "chef_counter",
        "title": "Chef's Counter Tasting Walk",
        "description": "Sample progressive bites from tucked-away kitchens and night markets.",
        "category": "Foodie adventures",
        "image_url": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=80",
        "location_hint": "Street markets, izakayas, and dessert bars in one swoop.",
    },
    {
        "id": "temple_stories",
        "title": "Golden Hour Temple Stories",
        "description": "A historian-led wander through quiet shrines before the crowds appear.",
        "category": "Culture & history",
        "image_url": "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=80",
        "location_hint": "Sunrise courtyards, incense rituals, and local legends.",
    },
    {
        "id": "coastal_cycle",
        "title": "Coastal Sunrise Cycle",
        "description": "Ride the waterfront at dawn, then refuel with a farm-to-table brunch.",
        "category": "Outdoors & nature",
        "image_url": "https://images.unsplash.com/photo-1526481280695-3c46931c2ae9?auto=format&fit=crop&w=1200&q=80",
        "location_hint": "Sea breezes, hidden beaches, and artisanal coffee stops.",
    },
    {
        "id": "art_lab",
        "title": "Design District Studio Hop",
        "description": "Meet makers in their studios and craft a bespoke keepsake to take home.",
        "category": "Something eclectic",
        "image_url": "https://images.unsplash.com/photo-1529429617124-aee3713d8e2f?auto=format&fit=crop&w=1200&q=80",
        "location_hint": "Boutique ateliers, galleries, and concept stores in bloom.",
    },
    {
        "id": "forest_baths",
        "title": "Forest Bathing & Tea Ritual",
        "description": "Slow down with a guided forest walk that ends in a mindful tea ceremony.",
        "category": "Outdoors & nature",
        "image_url": "https://images.unsplash.com/photo-1469474968028-56623f02e42e?auto=format&fit=crop&w=1200&q=80",
        "location_hint": "Whispering pines, mountain views, and calming traditions.",
    },
]



@dataclass
class _UserTurn:
    text: str
    payload: Optional[Dict[str, Any]] = None


@dataclass
class _StepResult:
    response: str
    next_step: Optional[str]
    require_clarifier: bool = False


_CONVERSATION_FLOW = [
    "group",
    "date_mode",
    "timing",
    "vibe",
    "pace",
    "budget",
    "notes",
]


def _initial_conversation_state(destination: str) -> Dict[str, Any]:
    return {
        "messages": [],
        "step_index": 0,
        "last_prompt_step": None,
        "pending_clarifier": None,
        "destination": destination,
        "timing_acknowledged": False,
    }


def _conversation_state(state: Dict[str, object]) -> Dict[str, Any]:
    destination = str(state.get("destination", ""))
    conversation = state.setdefault(
        "conversation",
        _initial_conversation_state(destination),
    )
    if conversation.get("destination") != destination:
        conversation = _initial_conversation_state(destination)
        state["conversation"] = conversation
    return conversation


def _current_step(conversation: Dict[str, Any]) -> Optional[str]:
    step_index = int(conversation.get("step_index", 0))
    if 0 <= step_index < len(_CONVERSATION_FLOW):
        return _CONVERSATION_FLOW[step_index]
    return None


def _set_step(conversation: Dict[str, Any], step_id: Optional[str]) -> None:
    if step_id is None:
        conversation["step_index"] = len(_CONVERSATION_FLOW)
        conversation["last_prompt_step"] = None
        return
    if step_id not in _CONVERSATION_FLOW:
        conversation["step_index"] = len(_CONVERSATION_FLOW)
        conversation["last_prompt_step"] = None
        return
    conversation["step_index"] = _CONVERSATION_FLOW.index(step_id)
    conversation["last_prompt_step"] = None


def _prompt_for_step(step_id: str, state: Dict[str, object]) -> str:
    destination = state.get("destination") or "your trip"
    prompts = {
        "group": f"Who's joining you for the adventure to **{destination}**?",
        "date_mode": "Do you have set dates in mind or are you flexible on timing?",
        "timing": "Share the dates or months that would work best and I'll lock them in.",
        "vibe": "What kind of vibe are you craving—nightlife, culture, nature?",
        "pace": "Should the days feel laid back, balanced, or totally packed?",
        "budget": "Any budget guardrails I should respect?",
        "notes": "Anything else that's a must-do or deal-breaker?",
    }
    return prompts.get(step_id, "Tell me more about the trip.")


def _append_message(conversation: Dict[str, Any], role: str, content: str) -> None:
    conversation.setdefault("messages", []).append({"role": role, "content": content})


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _extract_group_type(text: str) -> Optional[str]:
    lowered = _normalise(text)
    for option in _GROUP_TYPES:
        if option.lower() in lowered:
            return option

    keyword_map = {
        "solo": "Just me",
        "alone": "Just me",
        "myself": "Just me",
        "partner": "Partner getaway",
        "spouse": "Partner getaway",
        "girlfriend": "Partner getaway",
        "boyfriend": "Partner getaway",
        "wife": "Partner getaway",
        "husband": "Partner getaway",
        "couple": "Partner getaway",
        "family": "Family crew",
        "kids": "Family crew",
        "parents": "Family crew",
        "friends": "Friends trip",
        "buddies": "Friends trip",
        "mates": "Friends trip",
        "crew": "Friends trip",
        "cowork": "Workmates",
        "colleague": "Workmates",
        "team": "Workmates",
        "office": "Workmates",
    }
    for keyword, option in keyword_map.items():
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
            size = int(digits[0])
            if size > 0:
                return size
        except ValueError:
            pass

    lowered = _normalise(text)
    for word, value in _NUMBER_WORDS.items():
        if word in lowered:
            return value

    keyword_map = {
        "couple": 2,
        "pair": 2,
        "duo": 2,
        "solo": 1,
        "myself": 1,
        "family": 4,
    }
    for keyword, value in keyword_map.items():
        if keyword in lowered:
            return value
    return None


def _infer_date_mode(text: str) -> Optional[str]:
    lowered = _normalise(text)
    if any(token in lowered for token in ("flex", "open", "anytime", "not sure", "depends")):
        return "months"
    month_tokens = [
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
    if any(month in lowered for month in month_tokens):
        return "dates"
    if re.search(r"\d", lowered):
        return "dates"
    if "specific" in lowered:
        return "dates"
    if "month" in lowered:
        return "months"
    return None


_VIBE_KEYWORDS = {
    "night": "Nightlife",
    "club": "Nightlife",
    "bar": "Nightlife",
    "food": "Foodie adventures",
    "eat": "Foodie adventures",
    "restaurant": "Foodie adventures",
    "culinary": "Foodie adventures",
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
    selected: List[str] = []
    for option in _VIBE_OPTIONS:
        if option.lower() in lowered:
            selected.append(option)
    for keyword, option in _VIBE_KEYWORDS.items():
        if keyword in lowered and option not in selected:
            selected.append(option)
    # Support comma-separated values matching options exactly
    for chunk in re.split(r"[,/]| and ", lowered):
        chunk = chunk.strip()
        for option in _VIBE_OPTIONS:
            if chunk == option.lower():
                if option not in selected:
                    selected.append(option)
    return selected


def _infer_travel_pace(text: str) -> Optional[str]:
    lowered = _normalise(text)
    if any(token in lowered for token in ("relax", "slow", "chill", "easy", "unhurried")):
        return "Laid back"
    if any(token in lowered for token in ("balanced", "mix", "somewhere", "medium", "moderate")):
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


def _handle_group_turn(
    user_turn: _UserTurn, state: Dict[str, object], conversation: Dict[str, Any]
) -> _StepResult:
    payload = user_turn.payload or {}
    group_type = payload.get("group_type") or _extract_group_type(user_turn.text)
    group_size = payload.get("group_size") or _extract_group_size(user_turn.text)

    if group_type:
        state["group_type"] = group_type
    if group_size:
        state["group_size"] = int(group_size)

    if not (group_type or group_size):
        return _StepResult(
            "I didn't catch the crew just yet. Tap a quick pick or describe who's travelling with you.",
            next_step="group",
            require_clarifier=True,
        )

    final_type = str(state.get("group_type", "your crew"))
    final_size = int(state.get("group_size", 1))
    summary = f"Awesome—{final_size} traveller{'s' if final_size != 1 else ''} on a {final_type.lower()} vibe."
    return _StepResult(summary, next_step="date_mode")


def _handle_date_mode_turn(
    user_turn: _UserTurn, state: Dict[str, object], conversation: Dict[str, Any]
) -> _StepResult:
    payload = user_turn.payload or {}
    mode = payload.get("date_mode") or _infer_date_mode(user_turn.text)
    if mode not in ("dates", "months"):
        return _StepResult(
            "Are you thinking of specific dates or keeping things flexible? Use the buttons below to choose.",
            next_step="date_mode",
            require_clarifier=True,
        )

    if mode == "dates":
        state["date_mode"] = "dates"
        state["flexible_months"] = []
        message = "Great, let's lock in the exact days."
    else:
        state["date_mode"] = "months"
        state["start_date"] = None
        state["end_date"] = None
        message = "Keeping it flexible—tell me which months feel right."

    conversation["timing_acknowledged"] = False
    return _StepResult(message, next_step="timing")


def _handle_timing_turn(
    user_turn: _UserTurn, state: Dict[str, object], conversation: Dict[str, Any]
) -> _StepResult:
    payload = user_turn.payload or {}
    mode = state.get("date_mode", "dates")

    if mode == "dates":
        start_date = payload.get("start_date")
        end_date = payload.get("end_date")
        if start_date and end_date:
            state["start_date"] = start_date
            state["end_date"] = end_date
            state["flexible_months"] = []
            conversation["timing_acknowledged"] = True
            summary = (
                "Locked in your window from "
                f"{start_date.strftime('%b %d, %Y')} to {end_date.strftime('%b %d, %Y')}."
            )
            return _StepResult(summary, next_step="vibe")
    else:
        months = payload.get("flexible_months") or []
        if months:
            state["flexible_months"] = months
            state["start_date"] = None
            state["end_date"] = None
            conversation["timing_acknowledged"] = True
            month_labels = [
                date.fromisoformat(month).strftime("%B %Y") for month in months
            ]
            summary = "Staying flexible across " + ", ".join(month_labels)
            return _StepResult(summary, next_step="vibe")

    if not conversation.get("timing_acknowledged"):
        conversation["timing_acknowledged"] = True
        prompt = (
            "Love that! Use the selector below to set the exact window so I can plan around it."
        )
    else:
        prompt = "Give the selector a tap when you're ready and I'll take it from there."
    return _StepResult(prompt, next_step="timing", require_clarifier=True)


def _handle_vibe_turn(
    user_turn: _UserTurn, state: Dict[str, object], conversation: Dict[str, Any]
) -> _StepResult:
    payload = user_turn.payload or {}
    provided = payload.get("vibe")
    if isinstance(provided, list):
        vibes = [str(option) for option in provided if option in _VIBE_OPTIONS]
    else:
        vibes = _extract_vibes(user_turn.text)

    if not vibes:
        return _StepResult(
            "I didn't spot any vibe keywords. Pick a few from the chips below or describe them again.",
            next_step="vibe",
            require_clarifier=True,
        )

    current_vibes = set(state.get("vibe", []))
    current_vibes.update(vibes)
    state["vibe"] = sorted(current_vibes)
    chips = " ".join(f"`{item}`" for item in sorted(current_vibes))
    summary = f"Dialling in on {chips}."
    return _StepResult(summary, next_step="pace")


def _handle_pace_turn(
    user_turn: _UserTurn, state: Dict[str, object], conversation: Dict[str, Any]
) -> _StepResult:
    payload = user_turn.payload or {}
    pace = payload.get("travel_pace") or _infer_travel_pace(user_turn.text)
    if pace not in _PACE_OPTIONS:
        return _StepResult(
            "Want things chill, balanced, or full throttle? Use the toggle below to choose.",
            next_step="pace",
            require_clarifier=True,
        )

    state["travel_pace"] = pace
    summary = f"Got it—I'll keep the itinerary feeling **{pace.lower()}**."
    return _StepResult(summary, next_step="budget")


def _handle_budget_turn(
    user_turn: _UserTurn, state: Dict[str, object], conversation: Dict[str, Any]
) -> _StepResult:
    payload = user_turn.payload or {}
    budget = payload.get("budget") or _infer_budget(user_turn.text)
    if budget not in _BUDGET_OPTIONS:
        return _StepResult(
            "Give me a sense of the budget—grab a quick option below if that helps.",
            next_step="budget",
            require_clarifier=True,
        )

    state["budget"] = budget
    summary = f"Locked in a **{budget.lower()}** budget vibe."
    return _StepResult(summary, next_step="notes")


def _handle_notes_turn(
    user_turn: _UserTurn, state: Dict[str, object], conversation: Dict[str, Any]
) -> _StepResult:
    payload = user_turn.payload or {}
    note = payload.get("notes") or user_turn.text
    cleaned = note.strip()
    existing = str(state.get("notes", "")).strip()
    if cleaned:
        state["notes"] = cleaned if not existing else f"{existing}\n{cleaned}"
        message = "Perfect. I'll keep those extra details in mind."
    else:
        message = "No extra notes—I'll keep things streamlined."

    wrap = (
        message
        + "\n\nYou're all set! Jump to the inspiration gallery when you're ready to pick experiences."
    )
    return _StepResult(wrap, next_step=None)


_STEP_HANDLERS = {
    "group": _handle_group_turn,
    "date_mode": _handle_date_mode_turn,
    "timing": _handle_timing_turn,
    "vibe": _handle_vibe_turn,
    "pace": _handle_pace_turn,
    "budget": _handle_budget_turn,
    "notes": _handle_notes_turn,
}


def _render_group_clarifier(container, state: Dict[str, object]) -> Optional[_UserTurn]:
    selection: Optional[_UserTurn] = None
    defaults = {
        "Just me": 1,
        "Partner getaway": 2,
        "Family crew": 4,
        "Friends trip": 4,
        "Workmates": 4,
    }
    with container.chat_message("assistant"):
        st.markdown("Need a quick pick? Choose a crew style or set the headcount below.")
        col1, col2 = st.columns(2)
        for idx, option in enumerate(_GROUP_TYPES):
            target = col1 if idx % 2 == 0 else col2
            if target.button(option, key=f"plan_group_option_{idx}"):
                selection = _UserTurn(
                    text=f"{option}",
                    payload={
                        "group_type": option,
                        "group_size": defaults.get(option, state.get("group_size", 2)),
                    },
                )
        slider_value = st.slider(
            "How many travellers?",
            min_value=1,
            max_value=12,
            value=int(state.get("group_size", 2)),
            key="plan_group_size_slider",
        )
        if st.button("Use this headcount", key="plan_group_size_confirm"):
            selection = _UserTurn(
                text=f"{slider_value} travellers",
                payload={"group_size": slider_value},
            )
    return selection


def _render_date_mode_clarifier(container) -> Optional[_UserTurn]:
    selection: Optional[_UserTurn] = None
    with container.chat_message("assistant"):
        st.markdown("How are you thinking about timing?")
        col1, col2 = st.columns(2)
        if col1.button("Specific dates", key="plan_date_mode_dates"):
            selection = _UserTurn(
                text="Specific dates",
                payload={"date_mode": "dates"},
            )
        if col2.button("I'm flexible", key="plan_date_mode_flexible"):
            selection = _UserTurn(
                text="I'm flexible",
                payload={"date_mode": "months"},
            )
    return selection


def _render_timing_clarifier(container, state: Dict[str, object]) -> Optional[_UserTurn]:
    mode = state.get("date_mode", "dates")
    if mode == "dates":
        today = date.today()
        default_start = state.get("start_date") or today + timedelta(days=30)
        default_end = state.get("end_date") or default_start + timedelta(days=4)
        with container.chat_message("assistant"):
            st.markdown("Lock in the travel window so I can plan around it.")
            selected_dates = st.date_input(
                "Travel window",
                value=(default_start, default_end),
                min_value=today,
                key="plan_conversation_dates",
            )
            confirm = st.button("Use these dates", key="plan_conversation_dates_confirm")
            if confirm:
                if isinstance(selected_dates, tuple):
                    start_date, end_date = selected_dates
                else:
                    start_date = end_date = selected_dates
                if start_date and end_date:
                    return _UserTurn(
                        text=f"{start_date.strftime('%b %d, %Y')} – {end_date.strftime('%b %d, %Y')}",
                        payload={
                            "start_date": start_date,
                            "end_date": end_date,
                            "flexible_months": [],
                        },
                    )
    else:
        iso_values, labels = _month_options()
        default_labels = [
            labels[value]
            for value in state.get("flexible_months", [])
            if value in labels
        ]
        with container.chat_message("assistant"):
            st.markdown("Pick a few months that could work.")
            selection = st.multiselect(
                "Flexible months",
                options=[labels[value] for value in iso_values],
                default=default_labels,
                key="plan_conversation_months",
            )
            confirm = st.button("Use these months", key="plan_conversation_months_confirm")
            if confirm:
                if not selection:
                    st.warning("Select at least one month to keep things flexible.")
                else:
                    reverse_lookup = {label: iso for iso, label in labels.items()}
                    chosen = [reverse_lookup[label] for label in selection]
                    return _UserTurn(
                        text=", ".join(selection),
                        payload={
                            "flexible_months": chosen,
                            "start_date": None,
                            "end_date": None,
                        },
                    )
    return None


def _render_vibe_clarifier(container, state: Dict[str, object]) -> Optional[_UserTurn]:
    with container.chat_message("assistant"):
        st.markdown("Tap a few vibe tags that feel right.")
        default = [option for option in state.get("vibe", []) if option in _VIBE_OPTIONS]
        selection = st.multiselect(
            "Vibe picks",
            options=_VIBE_OPTIONS,
            default=default,
            key="plan_conversation_vibes",
        )
        if st.button("Lock these vibes", key="plan_conversation_vibes_confirm"):
            return _UserTurn(
                text=", ".join(selection) if selection else "No vibes",
                payload={"vibe": selection},
            )
    return None


def _render_pace_clarifier(container, state: Dict[str, object]) -> Optional[_UserTurn]:
    with container.chat_message("assistant"):
        st.markdown("Slide to the tempo that feels right for the trip.")
        default = state.get("travel_pace")
        if default not in _PACE_OPTIONS:
            default = _PACE_OPTIONS[1]
        pace_choice = st.select_slider(
            "Travel pace",
            options=_PACE_OPTIONS,
            value=default,
            key="plan_conversation_pace",
        )
        if st.button("Set this pace", key="plan_conversation_pace_confirm"):
            return _UserTurn(
                text=pace_choice,
                payload={"travel_pace": pace_choice},
            )
    return None


def _render_budget_clarifier(container, state: Dict[str, object]) -> Optional[_UserTurn]:
    with container.chat_message("assistant"):
        st.markdown("What's the budget vibe?")
        current = state.get("budget")
        index = _BUDGET_OPTIONS.index(current) if current in _BUDGET_OPTIONS else 1
        budget_choice = st.radio(
            "Budget", _BUDGET_OPTIONS, index=index, key="plan_conversation_budget"
        )
        if st.button("Confirm budget", key="plan_conversation_budget_confirm"):
            return _UserTurn(
                text=budget_choice,
                payload={"budget": budget_choice},
            )
    return None


_CLARIFIER_RENDERERS = {
    "group": _render_group_clarifier,
    "date_mode": lambda container, state: _render_date_mode_clarifier(container),
    "timing": _render_timing_clarifier,
    "vibe": _render_vibe_clarifier,
    "pace": _render_pace_clarifier,
    "budget": _render_budget_clarifier,
}


def _render_step_clarifier(
    container, state: Dict[str, object], step_id: str
) -> Optional[_UserTurn]:
    renderer = _CLARIFIER_RENDERERS.get(step_id)
    if not renderer:
        return None
    return renderer(container, state)




def _save_custom_interest(state: Dict[str, object]) -> None:
    """Persist a custom interest from the Streamlit text input."""

    entry = st.session_state.get("plan_custom_interest_entry", "")
    cleaned = entry.strip()
    if cleaned and cleaned not in state["custom_interests"]:
        state["custom_interests"].append(cleaned)
    st.session_state["plan_custom_interest_entry"] = ""


_LOGGER = logging.getLogger(__name__)


def ensure_plan_state() -> None:
    """Initialise the Streamlit session state used by the planner UI."""

    if _WIZARD_KEY not in st.session_state:
        st.session_state[_WIZARD_KEY] = {
            "scene": "welcome",
            "destination": "",
            "date_mode": "dates",
            "start_date": None,
            "end_date": None,
            "flexible_months": [],
            "group_type": _GROUP_TYPES[1],
            "group_size": 2,
            "travel_pace": _PACE_OPTIONS[1],
            "budget": _BUDGET_OPTIONS[1],
            "vibe": [],
            "custom_interests": [],
            "notes": "",
            "liked_cards": [],
            "saved_cards": [],
            "personal_events": [],
            "share_public": True,
            "share_caption": "",
            "allow_remix": True,
            "has_generated": False,
        }

    st.session_state.setdefault(_TRIP_INTENT_KEY, None)
    st.session_state.setdefault(_ITINERARY_KEY, None)
    st.session_state.setdefault(_PIPELINE_ERROR_KEY, None)


def _wizard_state() -> Dict[str, object]:
    return st.session_state[_WIZARD_KEY]


def _month_options() -> Tuple[List[str], Dict[str, str]]:
    today = date.today().replace(day=1)
    iso_values: List[str] = []
    labels: Dict[str, str] = {}
    for offset in range(0, 12):
        month = today + timedelta(days=offset * 31)
        real_month = date(month.year, month.month, 1)
        iso = real_month.isoformat()
        if iso in iso_values:
            continue
        label = real_month.strftime("%B %Y")
        iso_values.append(iso)
        labels[iso] = label
    return iso_values, labels


def _render_cinematic_intro(container, state: Dict[str, object]) -> None:
    container.markdown(
        """
        <div style="background: linear-gradient(120deg, #040b1a, #1c2b4d); padding: 3rem 2.4rem; border-radius: 24px;">
          <p style="color: rgba(255,255,255,0.75); letter-spacing: 0.2em; text-transform: uppercase; margin-bottom: 0.2rem;">Scene One</p>
          <h2 style="color: white; font-size: 2.8rem; margin: 0;">Where do you want to go?</h2>
          <p style="color: rgba(255,255,255,0.85); max-width: 640px; font-size: 1.05rem;">
            Picture sweeping drone shots and cinematic music. Drop the destination and we'll craft the opening act of your journey.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    destination = container.text_input(
        "Destination",
        value=str(state.get("destination", "")),
        key="plan_destination_input",
        placeholder="Kyoto, Lisbon, Reykjavik…",
    )
    state["destination"] = destination.strip()

    cta = container.button(
        "Start the adventure",
        type="primary",
        use_container_width=True,
        key="plan_start_cta",
    )
    if cta:
        if state["destination"]:
            state["scene"] = "conversation"
            st.session_state[_PIPELINE_ERROR_KEY] = None
        else:
            container.warning("Tell us where you're headed to roll the trailer.")

    container.caption("You can always come back to change the destination later.")


def _render_conversation(container, state: Dict[str, object]) -> None:
    conversation = _conversation_state(state)
    current_step = _current_step(conversation)

    if current_step and conversation.get("last_prompt_step") != current_step:
        prompt = _prompt_for_step(current_step, state)
        _append_message(conversation, "assistant", prompt)
        conversation["last_prompt_step"] = current_step
        st.experimental_rerun()

    messages: List[Dict[str, str]] = conversation.get("messages", [])
    for message in messages:
        role = message.get("role", "assistant")
        content = message.get("content", "")
        with container.chat_message(role):
            st.markdown(content)

    if current_step == "group" and conversation.get("pending_clarifier") is None:
        if not any(msg.get("role") == "user" for msg in messages):
            conversation["pending_clarifier"] = "group"

    user_turn: Optional[_UserTurn] = None
    if current_step:
        if conversation.get("pending_clarifier") == current_step:
            user_turn = _render_step_clarifier(container, state, current_step)

        if user_turn is None:
            placeholders = {
                "group": "Tell me about the crew…",
                "date_mode": "Share how locked-in your dates are…",
                "timing": "Drop the dates or months that work…",
                "vibe": "Tell me the vibe you're chasing…",
                "pace": "How intense should the days feel?",
                "budget": "Give me the budget vibe…",
                "notes": "Anything else I should keep in mind?",
            }
            placeholder = placeholders.get(current_step, "Type your reply…")
            user_input = st.chat_input(placeholder)
            if user_input:
                user_turn = _UserTurn(text=user_input)

    if current_step and user_turn:
        _append_message(conversation, "user", user_turn.text)
        handler = _STEP_HANDLERS.get(current_step)
        if handler:
            result = handler(user_turn, state, conversation)
            _append_message(conversation, "assistant", result.response)

            if result.next_step is None:
                _set_step(conversation, None)
                conversation["pending_clarifier"] = None
            else:
                if result.next_step != current_step:
                    _set_step(conversation, result.next_step)
                if result.require_clarifier:
                    conversation["pending_clarifier"] = result.next_step or current_step
                else:
                    conversation["pending_clarifier"] = None
        st.experimental_rerun()

    if current_step is None:
        container.success("Your planner brief is locked in.")
        action_cols = container.columns([1, 1])
        if action_cols[0].button("Update answers", key="plan_conversation_restart"):
            _set_step(conversation, "group")
            conversation["pending_clarifier"] = "group"
            st.experimental_rerun()
        if action_cols[1].button(
            "Next: Explore inspiration", key="plan_conversation_finish", type="primary"
        ):
            state["scene"] = "interests"

    if container.button("Back to cinematic intro", key="plan_back_intro"):
        state["scene"] = "welcome"


def _render_conversation_transcript(container, state: Dict[str, object]) -> None:
    conversation = state.get("conversation")
    if not isinstance(conversation, dict):
        return
    messages = conversation.get("messages", [])
    if not messages:
        return

    container.subheader("Trip setup recap")
    transcript_area = container.container()
    for message in messages:
        role = message.get("role", "assistant")
        content = message.get("content", "")
        with transcript_area.chat_message(role):
            st.markdown(content)


def _render_interest_gallery(container, state: Dict[str, object]) -> None:
    destination = state.get("destination") or "your trip"
    container.markdown(
        f"""
        ### Curate the vibe for {destination}
        Tap ❤️ to teach Meguru what you love and 🔖 to save it straight into your moodboard.
        """
    )

    if container.button("Back to questions", key="plan_back_conversation"):
        state["scene"] = "conversation"
        return

    vibe_tags = sorted(set(state.get("vibe", [])))
    if vibe_tags:
        chips = " ".join(f"`{tag}`" for tag in vibe_tags)
        container.caption(f"Dialling in on: {chips}")

    error_message = st.session_state.get(_PIPELINE_ERROR_KEY)
    if error_message:
        container.error(error_message)

    columns = container.columns(3, gap="large")
    for idx, card in enumerate(_EXPERIENCE_CARDS):
        target = columns[idx % len(columns)]
        with target:
            st.image(card["image_url"], use_container_width=True)
            st.markdown(f"**{card['title']}**")
            st.caption(card["description"])
            st.caption(f"_{card['location_hint']}_")
            like_key = f"plan_like_{card['id']}"
            save_key = f"plan_save_{card['id']}"
            liked = st.toggle("❤️ Like", key=like_key, value=card["id"] in state["liked_cards"])
            saved = st.toggle("🔖 Save", key=save_key, value=card["id"] in state["saved_cards"])
            if liked and card["id"] not in state["liked_cards"]:
                state["liked_cards"].append(card["id"])
            elif not liked and card["id"] in state["liked_cards"]:
                state["liked_cards"].remove(card["id"])

            if saved and card["id"] not in state["saved_cards"]:
                state["saved_cards"].append(card["id"])
            elif not saved and card["id"] in state["saved_cards"]:
                state["saved_cards"].remove(card["id"])

    container.text_input(
        "Add your own must-do (press enter to keep it)",
        key="plan_custom_interest_entry",
        placeholder="Vinyl record shops, rooftop yoga, tiny bookstores…",
    )
    container.button(
        "Save custom interest",
        key="plan_add_custom_interest",
        on_click=_save_custom_interest,
        kwargs={"state": state},
    )

    if state["custom_interests"]:
        container.write(
            "Custom interests: "
            + ", ".join(f"`{interest}`" for interest in state["custom_interests"])
        )

    generate_clicked = container.button(
        "Generate my itinerary",
        type="primary",
        use_container_width=True,
        key="plan_generate_itinerary",
    )
    if generate_clicked:
        success = _handle_submit(state)
        if success:
            return

    container.caption(
        "Want to tweak something? Head back to the questions or keep liking cards for a different mix."
    )


def _render_review(container, state: Dict[str, object]) -> None:
    container.markdown("### Your itinerary is live ✨")

    itinerary = st.session_state.get(_ITINERARY_KEY)
    intent: TripIntent | None = st.session_state.get(_TRIP_INTENT_KEY)

    if not itinerary or not intent:
        container.info(
            "Generate an itinerary to unlock sharing and remix features."
        )
        if container.button("Back to inspiration gallery", key="plan_review_back"):
            state["scene"] = "interests"
        return

    container.success(
        "Itinerary ready! Jump over to the **Itinerary** tab for the full cinematic breakdown."
    )

    bullets: List[str] = []
    if intent.start_date and intent.end_date:
        bullets.append(
            f"Dates: {intent.start_date.strftime('%b %d, %Y')} – {intent.end_date.strftime('%b %d, %Y')}"
        )
    elif state.get("flexible_months"):
        month_labels = [
            date.fromisoformat(month).strftime("%B %Y")
            for month in state["flexible_months"]
        ]
        bullets.append("Timing: flexible across " + ", ".join(month_labels))

    bullets.append(
        f"Crew: {state.get('group_type', 'Travelers')} (x{int(state.get('group_size', 1))})"
    )
    if intent.travel_pace:
        bullets.append(f"Pace: {intent.travel_pace}")
    if intent.budget:
        bullets.append(f"Budget: {intent.budget}")

    if bullets:
        container.markdown("- " + "\n- ".join(bullets))

    if state.get("personal_events"):
        container.markdown(
            "**Your personal additions**\n" + "\n".join(f"• {item}" for item in state["personal_events"])
        )

    container.markdown("#### Make it yours")
    custom_event = container.text_input(
        "Drop in your own moment",
        key="plan_custom_event_entry",
        placeholder="Sunset picnic at Arashiyama bamboo grove",
    )
    if container.button("Add to my itinerary", key="plan_add_custom_event"):
        cleaned = custom_event.strip()
        if cleaned and cleaned not in state["personal_events"]:
            state["personal_events"].append(cleaned)
        st.session_state["plan_custom_event_entry"] = ""

    container.markdown("#### Share the inspiration")
    share_public = container.toggle(
        "Share to the Meguru community feed",
        key="plan_share_public",
        value=bool(state.get("share_public", True)),
    )
    allow_remix = container.toggle(
        "Let other travellers remix this itinerary",
        key="plan_allow_remix",
        value=bool(state.get("allow_remix", True)),
    )
    share_caption = container.text_area(
        "Add a caption for your profile",
        value=str(state.get("share_caption", "")),
        key="plan_share_caption",
        placeholder="Tell the community why this trip is iconic…",
    )

    state.update(
        {
            "share_public": share_public,
            "allow_remix": allow_remix,
            "share_caption": share_caption.strip(),
        }
    )

    action_cols = container.columns([1, 1, 1])
    if action_cols[0].button("Explore more ideas", key="plan_review_more"):
        state["scene"] = "interests"
    if action_cols[1].button("Regenerate itinerary", key="plan_review_regen"):
        _handle_submit(state)
    if action_cols[2].button("Copy share link", key="plan_review_share"):
        container.info("Link copied! (Imagine social magic happening here.)")


def _build_trip_intent(state: Dict[str, object]) -> TripIntent:
    destination = str(state.get("destination", "")).strip()
    if not destination:
        raise ValueError("Destination is required")

    start_date = state.get("start_date")
    end_date = state.get("end_date")
    duration_days = None
    if isinstance(start_date, date) and isinstance(end_date, date) and end_date >= start_date:
        duration_days = (end_date - start_date).days + 1

    interests_set = set(state.get("vibe", [])) | set(state.get("custom_interests", []))
    liked_cards = set(state.get("liked_cards", []))
    saved_cards = set(state.get("saved_cards", []))
    for card in _EXPERIENCE_CARDS:
        if card["id"] in liked_cards or card["id"] in saved_cards:
            interests_set.add(card["category"])
            if card["id"] in saved_cards:
                interests_set.add(card["title"])

    notes_segments: List[str] = []
    if state.get("flexible_months"):
        months = ", ".join(
            date.fromisoformat(month).strftime("%B %Y")
            for month in state["flexible_months"]
        )
        notes_segments.append(f"Flexible timing: {months}")

    group_type = state.get("group_type")
    group_size = state.get("group_size")
    if group_type:
        notes_segments.append(f"Group: {group_type} ({int(group_size or 1)} travellers)")

    if state.get("personal_events"):
        notes_segments.append(
            "Personal additions: " + "; ".join(state["personal_events"])
        )

    existing_notes = str(state.get("notes", "")).strip()
    if existing_notes:
        notes_segments.append(existing_notes)

    combined_notes = "\n".join(notes_segments) if notes_segments else None

    return TripIntent(
        destination=destination,
        start_date=start_date if isinstance(start_date, date) else None,
        end_date=end_date if isinstance(end_date, date) else None,
        duration_days=duration_days,
        travel_pace=str(state.get("travel_pace")) if state.get("travel_pace") else None,
        budget=str(state.get("budget")) if state.get("budget") else None,
        interests=sorted(interests_set),
        notes=combined_notes,
    )


def _format_pipeline_error(exc: Exception) -> str:
    base_message = "Unable to generate the itinerary."
    details = str(exc).strip()
    if details:
        lowered = details.lower()
        if "google_maps_api_key" in lowered:
            return (
                f"{base_message} Add a Google Maps API key by setting the "
                "GOOGLE_MAPS_API_KEY environment variable."
            )
        if "openai" in lowered and any(token in lowered for token in ("api key", "401", "unauthorized")):
            return (
                f"{base_message} Provide an OpenAI API key via the "
                "OPENAI_API_KEY environment variable."
            )
        if "429" in lowered or "too many requests" in lowered:
            return (
                f"{base_message} The OpenAI API rate limit was hit. Wait a moment and try again."
            )
        return f"{base_message} {details}"
    return f"{base_message} Check your configuration and try again."


def _handle_submit(state: Dict[str, object]) -> bool:
    if not state.get("destination"):
        st.warning("Add a destination first.")
        return False

    try:
        intent = _build_trip_intent(state)
    except ValueError as exc:
        st.warning(str(exc))
        return False

    itinerary_placeholder = st.session_state.get(_ITINERARY_KEY)
    st.session_state[_TRIP_INTENT_KEY] = intent

    try:
        with st.spinner("Generating your itinerary…"):
            itinerary = run_trip_pipeline(intent)
    except Exception as exc:  # noqa: BLE001 - surfaced to the user
        friendly_message = _format_pipeline_error(exc)
        _LOGGER.exception("Trip pipeline failed")
        st.session_state[_PIPELINE_ERROR_KEY] = friendly_message
        st.session_state[_ITINERARY_KEY] = itinerary_placeholder
        st.error(friendly_message)
        return False

    st.session_state[_PIPELINE_ERROR_KEY] = None
    st.session_state[_ITINERARY_KEY] = itinerary
    st.session_state["_focus_itinerary"] = True
    state["scene"] = "review"
    state["has_generated"] = True
    st.success("Itinerary ready! Check the Itinerary tab for details.")
    return True


def render_plan_tab(container) -> None:
    """Render the plan wizard inside the provided container."""

    state = _wizard_state()

    with container:
        transcript_area = st.container()
        body_area = st.container()

        scene = state.get("scene", "welcome")

        if scene in {"interests", "review"}:
            _render_conversation_transcript(transcript_area, state)

        if scene == "welcome":
            _render_cinematic_intro(body_area, state)
        elif scene == "conversation":
            _render_conversation(body_area, state)
        elif scene == "interests":
            _render_interest_gallery(body_area, state)
        else:
            _render_review(body_area, state)
