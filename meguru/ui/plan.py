"""UI helpers for the cinematic trip planning journey."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Mapping, Optional, Tuple, TypedDict

import streamlit as st

from meguru.schemas import TripIntent
from meguru.workflows import PlanConversationUpdate, PlanConversationWorkflow
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
_MAX_GALLERY_CARDS = 4
_MIN_GALLERY_CARDS = 3
_ITINERARY_MIN_SELECTIONS = 3
_VIBE_OPTIONS = [
    "Nightlife",
    "Foodie adventures",
    "Culture & history",
    "Outdoors & nature",
    "Something eclectic",
]


class _CardSignals(TypedDict, total=False):
    """Optional metadata that helps rank cards against trip context."""

    vibes: List[str]
    pace: List[str]
    budget: List[str]
    duration: List[str]
    tags: List[str]
    group_types: List[str]
    tones: List[str]
    moods: List[str]


class _ExperienceCardRequired(TypedDict):
    id: str
    title: str
    description: str
    category: str
    image_url: str
    location_hint: str


class _ExperienceCardOptional(TypedDict, total=False):
    metadata: _CardSignals


class _ExperienceCard(_ExperienceCardRequired, _ExperienceCardOptional):
    """Static representation of an experience suggestion card."""


_EXPERIENCE_CARDS: List[_ExperienceCard] = [
    {
        "id": "neon_bazaar",
        "title": "Neon Night Bazaar Crawl",
        "description": "Slide into hidden bars, late-night bites, and rooftop lounges with a local host.",
        "category": "Nightlife",
        "image_url": "https://images.unsplash.com/photo-1504805572947-34fad45aed93?auto=format&fit=crop&w=1200&q=80",
        "location_hint": "Perfect for electric evenings and skyline views.",
        "metadata": {
            "vibes": ["Nightlife", "Something eclectic"],
            "pace": ["Balanced", "All-out"],
            "budget": ["Moderate", "Splurge"],
            "duration": ["short_break"],
            "tags": ["cocktails", "late-night", "skyline", "celebration"],
            "group_types": ["Friends trip", "Partner getaway", "Workmates"],
            "tones": ["high-energy"],
            "moods": ["celebration"],
        },
    },
    {
        "id": "chef_counter",
        "title": "Chef's Counter Tasting Walk",
        "description": "Sample progressive bites from tucked-away kitchens and night markets.",
        "category": "Foodie adventures",
        "image_url": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=80",
        "location_hint": "Street markets, izakayas, and dessert bars in one swoop.",
        "metadata": {
            "vibes": ["Foodie adventures", "Nightlife"],
            "pace": ["Balanced"],
            "budget": ["Moderate", "Splurge"],
            "duration": ["short_break", "week"],
            "tags": ["chef-led", "progressive dinner", "night market", "food tour"],
            "group_types": ["Partner getaway", "Friends trip"],
            "tones": ["indulgent", "romantic"],
            "moods": ["celebration"],
        },
    },
    {
        "id": "temple_stories",
        "title": "Golden Hour Temple Stories",
        "description": "A historian-led wander through quiet shrines before the crowds appear.",
        "category": "Culture & history",
        "image_url": "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=80",
        "location_hint": "Sunrise courtyards, incense rituals, and local legends.",
        "metadata": {
            "vibes": ["Culture & history", "Outdoors & nature"],
            "pace": ["Laid back", "Balanced"],
            "budget": ["Moderate"],
            "duration": ["short_break", "week"],
            "tags": ["sunrise", "storyteller", "rituals", "mindful"],
            "group_types": ["Just me", "Partner getaway", "Family crew"],
            "tones": ["reflective"],
            "moods": ["peaceful", "burned_out"],
        },
    },
    {
        "id": "coastal_cycle",
        "title": "Coastal Sunrise Cycle",
        "description": "Ride the waterfront at dawn, then refuel with a farm-to-table brunch.",
        "category": "Outdoors & nature",
        "image_url": "https://images.unsplash.com/photo-1526481280695-3c46931c2ae9?auto=format&fit=crop&w=1200&q=80",
        "location_hint": "Sea breezes, hidden beaches, and artisanal coffee stops.",
        "metadata": {
            "vibes": ["Outdoors & nature", "Something eclectic"],
            "pace": ["Balanced", "All-out"],
            "budget": ["Moderate"],
            "duration": ["short_break", "week"],
            "tags": ["sunrise", "cycling", "brunch", "active"],
            "group_types": ["Friends trip", "Partner getaway"],
            "tones": ["adventurous"],
            "moods": ["celebration"],
        },
    },
    {
        "id": "art_lab",
        "title": "Design District Studio Hop",
        "description": "Meet makers in their studios and craft a bespoke keepsake to take home.",
        "category": "Something eclectic",
        "image_url": "https://images.unsplash.com/photo-1529429617124-aee3713d8e2f?auto=format&fit=crop&w=1200&q=80",
        "location_hint": "Boutique ateliers, galleries, and concept stores in bloom.",
        "metadata": {
            "vibes": ["Something eclectic", "Culture & history"],
            "pace": ["Laid back", "Balanced"],
            "budget": ["Moderate", "Splurge"],
            "duration": ["week", "extended"],
            "tags": ["design", "workshop", "boutique", "creative"],
            "group_types": ["Just me", "Friends trip"],
            "tones": ["creative"],
            "moods": ["peaceful"],
        },
    },
    {
        "id": "forest_baths",
        "title": "Forest Bathing & Tea Ritual",
        "description": "Slow down with a guided forest walk that ends in a mindful tea ceremony.",
        "category": "Outdoors & nature",
        "image_url": "https://images.unsplash.com/photo-1469474968028-56623f02e42e?auto=format&fit=crop&w=1200&q=80",
        "location_hint": "Whispering pines, mountain views, and calming traditions.",
        "metadata": {
            "vibes": ["Outdoors & nature", "Something eclectic"],
            "pace": ["Laid back"],
            "budget": ["Shoestring", "Moderate"],
            "duration": ["week", "extended"],
            "tags": ["forest bathing", "tea ceremony", "wellness", "romantic"],
            "group_types": ["Partner getaway", "Just me"],
            "tones": ["soothing", "romantic"],
            "moods": ["peaceful", "burned_out"],
        },
    },
]



_CARD_LOOKUP: Dict[str, _ExperienceCard] = {card["id"]: card for card in _EXPERIENCE_CARDS}

_WORKFLOW_KEY = "_plan_conversation_workflow"

_PACE_TAG_LABELS = {
    "laid back": "slow pace",
    "balanced": "balanced pace",
    "all-out": "all-out pace",
}

_BUDGET_TAG_LABELS = {
    "shoestring": "budget-friendly",
    "moderate": "mid-range",
    "splurge": "premium",
}

_EVENT_KEYWORDS = {
    "anniversary": "anniversary",
    "honeymoon": "honeymoon",
    "birthday": "birthday trip",
    "proposal": "proposal",
    "babymoon": "babymoon",
}


_GROUP_TYPE_MATCH_WEIGHT = 1.4
_GROUP_TYPE_PARTIAL_WEIGHT = 0.3
_TONE_MATCH_WEIGHT = 0.8
_MOOD_MATCH_WEIGHT = 1.0
_OCCASION_MATCH_WEIGHT = 0.6

_OCCASION_TAG_HINTS = {
    "anniversary": {"romantic"},
    "honeymoon": {"romantic"},
    "proposal": {"romantic"},
    "babymoon": {"wellness", "calm"},
    "birthday": {"celebration"},
    "birthday trip": {"celebration"},
}


def _normalise_signal(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _coerce_positive_int(value: object) -> int | None:
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


def _infer_duration_bucket(state: Mapping[str, object]) -> str | None:
    """Approximate the requested trip duration to compare with card metadata."""

    start = state.get("start_date")
    end = state.get("end_date")
    if isinstance(start, date) and isinstance(end, date) and end >= start:
        days = (end - start).days + 1
        if days <= 3:
            return "short_break"
        if days <= 7:
            return "week"
        return "extended"

    timing_text = " ".join(
        str(state.get(key, ""))
        for key in ("timing_note", "notes")
        if state.get(key)
    ).lower()

    if any(term in timing_text for term in ["weekend", "3-day", "short trip", "mini break"]):
        return "short_break"
    if any(term in timing_text for term in ["week", "7-day", "itinerary"]):
        return "week"
    if any(term in timing_text for term in ["sabbatical", "extended", "month", "long stay"]):
        return "extended"
    return None


def _score_card(card: _ExperienceCard, state: Mapping[str, object]) -> float:
    metadata = card.get("metadata") or {}
    brief_data = state.get("trip_brief") if isinstance(state.get("trip_brief"), Mapping) else {}

    def _resolve_signal(key: str) -> object:
        value = state.get(key)
        if value:
            return value
        if isinstance(brief_data, Mapping):
            return brief_data.get(key)
        return None

    state_vibes = {
        _normalise_signal(item)
        for item in state.get("vibe", [])
        if isinstance(item, str) and item.strip()
    }
    card_vibes = {_normalise_signal(card.get("category", ""))}
    card_vibes.update(
        _normalise_signal(v)
        for v in metadata.get("vibes", []) or []
        if isinstance(v, str)
    )

    score = 1.0

    if state_vibes:
        matched_vibes = state_vibes & card_vibes
        if matched_vibes:
            score += 4 + len(matched_vibes)
        elif metadata.get("vibes"):
            score -= 0.5
    else:
        score += 0.5

    pace = _normalise_signal(_resolve_signal("travel_pace"))
    if pace:
        card_pace = {
            _normalise_signal(item)
            for item in metadata.get("pace", []) or []
            if isinstance(item, str)
        }
        if pace in card_pace:
            score += 2.5
        elif card_pace:
            score += 0.4

    budget = _normalise_signal(_resolve_signal("budget"))
    if budget:
        card_budget = {
            _normalise_signal(item)
            for item in metadata.get("budget", []) or []
            if isinstance(item, str)
        }
        if budget in card_budget:
            score += 2.0
        elif card_budget:
            score -= 0.3

    group_type = _normalise_signal(_resolve_signal("group_type"))
    if group_type:
        card_groups = {
            _normalise_signal(item)
            for item in metadata.get("group_types", []) or []
            if isinstance(item, str)
        }
        if group_type in card_groups:
            score += _GROUP_TYPE_MATCH_WEIGHT
        elif card_groups:
            score += _GROUP_TYPE_PARTIAL_WEIGHT

    tone = _normalise_signal(_resolve_signal("tone"))
    mood_signal = _normalise_signal(_resolve_signal("mood"))

    card_tones = {
        _normalise_signal(item)
        for item in metadata.get("tones", []) or []
        if isinstance(item, str)
    }
    if tone and card_tones:
        if tone in card_tones:
            score += _TONE_MATCH_WEIGHT
        else:
            score += 0.2

    card_moods = {
        _normalise_signal(item)
        for item in metadata.get("moods", []) or []
        if isinstance(item, str)
    }
    if mood_signal and card_moods:
        if mood_signal in card_moods:
            score += _MOOD_MATCH_WEIGHT
        else:
            score -= 0.2

    duration = _infer_duration_bucket(state)
    if duration:
        card_duration = {
            _normalise_signal(item)
            for item in metadata.get("duration", []) or []
            if isinstance(item, str)
        }
        if duration in card_duration:
            score += 1.5

    occasion = _normalise_signal(_resolve_signal("occasion"))
    if occasion:
        relevant_tags = _OCCASION_TAG_HINTS.get(occasion, set())
        if relevant_tags:
            card_tags = {
                _normalise_signal(tag)
                for tag in metadata.get("tags", []) or []
                if isinstance(tag, str)
            }
            if card_tags & relevant_tags:
                score += _OCCASION_MATCH_WEIGHT

    custom_interests = {
        _normalise_signal(item)
        for item in state.get("custom_interests", [])
        if isinstance(item, str) and item.strip()
    }
    if custom_interests:
        searchable_text = " ".join(
            [
                card.get("title", ""),
                card.get("description", ""),
                card.get("location_hint", ""),
            ]
            + [
                str(tag)
                for tag in metadata.get("tags", []) or []
                if isinstance(tag, str)
            ]
        ).lower()
        for interest in custom_interests:
            if interest and interest in searchable_text:
                score += 1.0

    return score


def _collect_active_tags(state: Mapping[str, object]) -> List[str]:
    tags: List[str] = []
    for vibe in state.get("vibe", []) or []:
        if isinstance(vibe, str) and vibe.strip():
            tags.append(_normalise_signal(vibe))

    pace_value = state.get("travel_pace")
    pace = _normalise_signal(pace_value)
    if pace and isinstance(pace_value, str):
        label = _PACE_TAG_LABELS.get(pace, str(pace_value))
        tags.append(label)

    budget_value = state.get("budget")
    budget = _normalise_signal(budget_value)
    if budget and isinstance(budget_value, str):
        label = _BUDGET_TAG_LABELS.get(budget, str(budget_value))
        tags.append(label)

    note_text = " ".join(
        str(state.get(key, "")) for key in ("notes", "timing_note") if state.get(key)
    ).lower()
    for keyword, label in _EVENT_KEYWORDS.items():
        if keyword in note_text and label not in tags:
            tags.append(label)

    return tags


def _workflow() -> PlanConversationWorkflow:
    workflow = st.session_state.get(_WORKFLOW_KEY)
    if not isinstance(workflow, PlanConversationWorkflow):
        workflow = PlanConversationWorkflow()
        st.session_state[_WORKFLOW_KEY] = workflow
    return workflow


def _conversation_log(state: Dict[str, object]) -> List[Dict[str, str]]:
    conversation = PlanConversationWorkflow.ensure_conversation(state)
    messages = conversation.get("messages")
    if isinstance(messages, list):
        return messages
    conversation["messages"] = []
    return conversation["messages"]


def _ensure_conversation_intro(state: Dict[str, object]) -> None:
    conversation = PlanConversationWorkflow.ensure_conversation(state)
    messages = conversation.get("messages")
    if not isinstance(messages, list):
        conversation["messages"] = []
        messages = conversation["messages"]
    if messages:
        return
    conversation.pop("gallery_message_index", None)
    intro = (
        "Hey there! ✨ Where are we headed? Start me with the destination, then fill me in "
        "on the crew, timing, and the vibe so I can sculpt the brief."
    )
    messages.append({"role": "assistant", "content": intro})


def _card_payload(card_id: str) -> Dict[str, Any]:
    details = _CARD_LOOKUP.get(card_id)
    if not details:
        return {"id": card_id}
    return dict(details)


def _sync_activity_preferences(state: Dict[str, object]) -> None:
    """Ensure the planner state keeps full payloads for liked and saved cards."""

    catalog: Mapping[str, Mapping[str, Any]] = (
        state.get("_activity_catalog", {}) or {}
    )  # type: ignore[assignment]

    existing_liked = {
        str(item.get("id")): item
        for item in state.get("liked_inspirations", [])
        if isinstance(item, Mapping) and item.get("id")
    }
    existing_saved = {
        str(item.get("id")): item
        for item in state.get("saved_inspirations", [])
        if isinstance(item, Mapping) and item.get("id")
    }

    def _collect(
        card_ids: List[str],
        *,
        priority: str,
        existing: Dict[str, Mapping[str, Any]],
    ) -> List[Dict[str, Any]]:
        collected: List[Dict[str, Any]] = []
        for card_id in card_ids:
            details: Mapping[str, Any] | None = catalog.get(card_id)  # type: ignore[arg-type]
            if not details:
                details = existing.get(card_id)
            if not details:
                details = _card_payload(card_id)
            payload = dict(details)
            payload.setdefault("id", card_id)
            payload.setdefault("priority", priority)
            collected.append(payload)
        return collected

    state["saved_inspirations"] = _collect(
        [str(card_id) for card_id in state.get("saved_cards", [])],
        priority="saved",
        existing=existing_saved,
    )
    state["liked_inspirations"] = _collect(
        [str(card_id) for card_id in state.get("liked_cards", [])],
        priority="liked",
        existing=existing_liked,
    )


def _run_plan_action(
    state: Dict[str, object],
    action: Dict[str, Any],
    *,
    container=None,
) -> None:
    workflow = _workflow()
    update = workflow.process_action(state, action)
    messages = _conversation_log(state)
    conversation = state.get("conversation") or {}

    if update.user_message:
        messages.append({"role": "user", "content": update.user_message})
        if container is not None:
            with container.chat_message("user"):
                st.markdown(update.user_message)

    if update.assistant_chunks:
        assembled_chunks: List[str] = []
        if container is not None:
            with container.chat_message("assistant"):
                placeholder = st.empty()
                for chunk in update.assistant_chunks:
                    assembled_chunks.append(chunk)
                    placeholder.markdown("\n\n".join(assembled_chunks))
        else:
            assembled_chunks.extend(update.assistant_chunks)

        combined = "\n\n".join(assembled_chunks)
        scene = _resolve_scene(conversation, state, update)
        payload: Dict[str, Any] = {"role": "assistant", "content": combined}
        if scene:
            payload["scene"] = scene
        messages.append(payload)
        if scene == "gallery":
            conversation.setdefault("gallery_message_index", len(messages) - 1)


def _resolve_scene(
    conversation: Mapping[str, Any],
    state: Mapping[str, Any],
    update: PlanConversationUpdate,
) -> str | None:
    if getattr(update, "clarifier_active", False):
        return "clarifier"

    pending = conversation.get("pending_fields") if isinstance(conversation, Mapping) else None
    if pending:
        return "pending"

    if PlanConversationWorkflow.ready_for_gallery(state):
        return "gallery"

    return None


def _render_conversation(container, state: Dict[str, object]) -> None:
    workflow = _workflow()
    conversation = workflow.ensure_conversation(state)
    _ensure_conversation_intro(state)

    messages = _conversation_log(state)

    has_user_message = any(message.get("role") == "user" for message in messages)
    if not has_user_message:
        intro_container = container.container()
        _render_cinematic_intro(intro_container, state)

    for index, message in enumerate(messages):
        role = message.get("role", "assistant")
        content = message.get("content", "")
        with container.chat_message(role):
            st.markdown(content)
            if role == "assistant":
                _render_scene(st, state, message, index=index)

    user_text = st.chat_input(
        "Start with the destination, then sprinkle in the crew, timing, and vibe…"
    )
    if user_text:
        _run_plan_action(state, {"type": "message", "text": user_text}, container=container)

    if container.button("View cinematic intro", key="plan_back_intro"):
        state["scene"] = "welcome"


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
            "scene": "conversation",
            "destination": "",
            "date_mode": "dates",
            "start_date": None,
            "end_date": None,
            "flexible_months": [],
            "group_type": None,
            "group_size": None,
            "travel_pace": None,
            "budget": None,
            "vibe": [],
            "custom_interests": [],
            "notes": "",
            "timing_note": None,
            "liked_cards": [],
            "saved_cards": [],
            "liked_inspirations": [],
            "saved_inspirations": [],
            "_activity_catalog": {},
            "trip_brief": {},
            "personal_events": [],
            "share_public": True,
            "share_caption": "",
            "allow_remix": True,
            "has_generated": False,
            "conversation": {"messages": [], "pending_fields": []},
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
    _ensure_conversation_intro(state)

    container.markdown(
        """
        <div style="background: linear-gradient(120deg, #040b1a, #1c2b4d); padding: 3rem 2.4rem; border-radius: 24px;">
          <p style="color: rgba(255,255,255,0.75); letter-spacing: 0.2em; text-transform: uppercase; margin-bottom: 0.2rem;">Scene One</p>
          <h2 style="color: white; font-size: 2.8rem; margin: 0;">Where do you want to go?</h2>
          <p style="color: rgba(255,255,255,0.85); max-width: 640px; font-size: 1.05rem;">
            Picture sweeping drone shots and cinematic music. Drop your opening brief in the chat and we'll craft the first act of your journey.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    container.caption("Start the conversation below—destination, crew, vibes, I'm listening.")


def _prepare_activity_cards(
    state: Dict[str, object]
) -> Tuple[List[_ExperienceCard], set[str], set[str]]:
    catalog = state.setdefault("_activity_catalog", {})
    if not isinstance(catalog, dict):  # pragma: no cover - defensive fallback
        catalog = dict(catalog)
        state["_activity_catalog"] = catalog

    previous_likes = set(state.get("liked_cards", []))
    previous_saves = set(state.get("saved_cards", []))
    forced_ids = previous_likes | previous_saves

    ranked_cards: List[Tuple[float, _ExperienceCard]] = []
    for card in _EXPERIENCE_CARDS:
        score = _score_card(card, state)
        if card["id"] in previous_likes or card["id"] in previous_saves:
            score += 5
        ranked_cards.append((score, card))

    ranked_cards.sort(key=lambda item: item[0], reverse=True)

    target_count = min(_MAX_GALLERY_CARDS, len(_EXPERIENCE_CARDS))
    target_count = max(target_count, _MIN_GALLERY_CARDS)
    if len(forced_ids) > target_count:
        target_count = len(forced_ids)

    selected_cards: List[_ExperienceCard] = []
    selected_ids: set[str] = set()

    for _, card in ranked_cards:
        if card["id"] in forced_ids and card["id"] not in selected_ids:
            selected_cards.append(card)
            selected_ids.add(card["id"])

    for _, card in ranked_cards:
        if card["id"] in selected_ids:
            continue
        if len(selected_cards) >= target_count:
            break
        selected_cards.append(card)
        selected_ids.add(card["id"])

    if not selected_cards:
        selected_cards = [card for _, card in ranked_cards]

    for card in selected_cards:
        catalog[str(card["id"])] = dict(card)

    return selected_cards, previous_likes, previous_saves


def _render_activity_cards(container, state: Dict[str, object]) -> None:
    selected_cards, previous_likes, previous_saves = _prepare_activity_cards(state)

    like_inputs: Dict[str, bool] = {}
    save_inputs: Dict[str, bool] = {}

    columns = container.columns(3, gap="large") if selected_cards else []
    for idx, card in enumerate(selected_cards):
        target = columns[idx % len(columns)] if columns else container
        with target:
            st.image(card["image_url"], use_container_width=True)
            st.markdown(f"**{card['title']}**")
            st.caption(card["description"])
            st.caption(f"_{card['location_hint']}_")
            like_key = f"plan_like_{card['id']}"
            save_key = f"plan_save_{card['id']}"
            like_inputs[card["id"]] = st.toggle(
                "❤️ Like", key=like_key, value=card["id"] in previous_likes
            )
            save_inputs[card["id"]] = st.toggle(
                "🔖 Save", key=save_key, value=card["id"] in previous_saves
            )

    current_likes = {card_id for card_id, liked in like_inputs.items() if liked}
    current_saves = {card_id for card_id, saved in save_inputs.items() if saved}

    for card_id in current_likes - previous_likes:
        _run_plan_action(state, {"type": "like_activity", "card": _card_payload(card_id)})
    for card_id in previous_likes - current_likes:
        _run_plan_action(state, {"type": "unlike_activity", "card": _card_payload(card_id)})

    for card_id in current_saves - previous_saves:
        _run_plan_action(state, {"type": "save_activity", "card": _card_payload(card_id)})
    for card_id in previous_saves - current_saves:
        _run_plan_action(state, {"type": "unsave_activity", "card": _card_payload(card_id)})

    _sync_activity_preferences(state)


def _compose_gallery_transition(state: Mapping[str, object]) -> str | None:
    brief = state.get("trip_brief") if isinstance(state.get("trip_brief"), Mapping) else {}
    if not isinstance(brief, Mapping):
        brief = {}

    raw_vibes = brief.get("vibes") if isinstance(brief.get("vibes"), list) else []
    vibes = [v for v in raw_vibes if isinstance(v, str) and v.strip()]
    pace = brief.get("travel_pace") if isinstance(brief.get("travel_pace"), str) else None
    budget = brief.get("budget") if isinstance(brief.get("budget"), str) else None
    group_type = brief.get("group_type") if isinstance(brief.get("group_type"), str) else None

    fragments: List[str] = []
    if vibes:
        vibe_label = " + ".join(v.strip().lower() for v in vibes[:2])
        fragments.append(f"{vibe_label} energy")
    if pace:
        fragments.append(f"{pace.strip().lower()} pacing")
    if budget:
        fragments.append(f"{budget.strip().lower()} budget lane")
    if group_type:
        fragments.append(f"for the {group_type.strip().lower()} crew")

    if not fragments:
        return None

    if len(fragments) == 1:
        descriptor = fragments[0]
    else:
        descriptor = ", ".join(fragments[:-1]) + f" and {fragments[-1]}"

    subject = brief.get("destination")
    if not isinstance(subject, str) or not subject.strip():
        subject = str(state.get("destination") or "this journey").strip()

    if not subject:
        subject = "this journey"

    return f"You're leaning into that {descriptor} for {subject}. Here's what that could look like."


def _gallery_micro_intro(state: Mapping[str, object]) -> str | None:
    """Compose a brief cinematic line for the gallery scene."""

    transition = _compose_gallery_transition(state)
    if transition:
        return transition

    destination = state.get("destination")
    if destination:
        subject = str(destination).strip()
    else:
        subject = "this journey"

    if not subject:
        subject = "this journey"

    return (
        f"A quick montage over {subject}—neon glow, dawn horizons, and moments waiting to be claimed."
    )


def _itinerary_ready_line(state: Mapping[str, object], selection_count: int) -> str | None:
    if selection_count < _ITINERARY_MIN_SELECTIONS:
        return None

    brief = state.get("trip_brief") if isinstance(state.get("trip_brief"), Mapping) else {}
    destination = None
    if isinstance(brief, Mapping):
        destination = brief.get("destination")
    if not isinstance(destination, str) or not destination.strip():
        destination = str(state.get("destination") or "this trip").strip()
    if not destination:
        destination = "this trip"

    vibe_fragment = None
    if isinstance(brief, Mapping):
        raw_vibes = brief.get("vibes") if isinstance(brief.get("vibes"), list) else []
        vibes = [v for v in raw_vibes if isinstance(v, str) and v.strip()]
        if vibes:
            vibe_fragment = " + ".join(v.strip().lower() for v in vibes[:2]) + " energy"

    pace = None
    if isinstance(brief, Mapping):
        raw_pace = brief.get("travel_pace")
        if isinstance(raw_pace, str) and raw_pace.strip():
            pace = f"{raw_pace.strip().lower()} pacing"

    descriptors = [fragment for fragment in [vibe_fragment, pace] if fragment]
    if descriptors:
        if len(descriptors) == 1:
            detail = descriptors[0]
        else:
            detail = " and ".join(descriptors)
        return (
            f"{selection_count} experiences locked for {destination}. Ready for me to weave "
            f"that {detail} into your itinerary?"
        )

    return f"{selection_count} experiences locked. Ready for me to weave them into your itinerary?"


def _render_interest_gallery(container, state: Dict[str, object]) -> None:
    intro = _gallery_micro_intro(state)
    if intro:
        container.markdown(f"_{intro}_")

    if container.button("Back to questions", key="plan_back_conversation"):
        state["scene"] = "conversation"
        return

    active_tags = _collect_active_tags(state)
    if active_tags:
        chips = " · ".join(active_tags)
        container.markdown(
            f"<p style='color: rgba(0, 0, 0, 0.55); margin-top: -0.2rem;'>"
            f"{chips}"
            "</p>",
            unsafe_allow_html=True,
        )

    error_message = st.session_state.get(_PIPELINE_ERROR_KEY)
    if error_message:
        container.error(error_message)

    _render_activity_cards(container, state)

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

    selected_ids = PlanConversationWorkflow._selected_card_ids(state)
    selection_count = len(selected_ids)

    if selection_count < _ITINERARY_MIN_SELECTIONS:
        container.caption(
            "Like or save at least three experiences to unlock the cinematic itinerary preview."
        )
    else:
        invite = _itinerary_ready_line(state, selection_count)
        if invite:
            container.markdown(f"_{invite}_")

    generate_clicked = container.button(
        "Generate my itinerary",
        type="primary",
        use_container_width=True,
        key="plan_generate_itinerary",
        disabled=selection_count < _ITINERARY_MIN_SELECTIONS,
    )
    if generate_clicked:
        success = _handle_submit(state)
        if success:
            return

def _render_pending_requirements(
    container, state: Mapping[str, object], *, emphasise: bool
) -> None:
    conversation = state.get("conversation") if isinstance(state, Mapping) else None
    pending: List[str] = []
    if isinstance(conversation, Mapping):
        pending = [
            str(field).replace("_", " ")
            for field in conversation.get("pending_fields", []) or []
            if field
        ]

    if not pending:
        return

    summary = ", ".join(pending)
    message = f"Still need: {summary}."
    if emphasise:
        container.info(message)
    else:
        container.caption(message)


def _render_scene(container, state: Dict[str, object], message: Mapping[str, Any], *, index: int) -> None:
    scene = message.get("scene") if isinstance(message, Mapping) else None
    if not scene:
        return

    if scene == "clarifier":
        _render_pending_requirements(container, state, emphasise=True)
        return

    if scene == "pending":
        _render_pending_requirements(container, state, emphasise=False)
        return

    if scene == "gallery":
        conversation = state.get("conversation") if isinstance(state, Mapping) else None
        anchor_index: Optional[int] = None
        if isinstance(conversation, dict):
            stored_index = conversation.get("gallery_message_index")
            if isinstance(stored_index, int):
                anchor_index = stored_index
            else:
                conversation["gallery_message_index"] = index
                anchor_index = index

        if anchor_index is not None and anchor_index != index:
            return

        container.success("Your brief is locked. Ready when you are to explore inspiration.")
        _render_activity_cards(container, state)


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

    group_type = state.get("group_type")
    group_size_int = _coerce_positive_int(state.get("group_size"))
    if group_type:
        size_suffix = f" (x{group_size_int})" if group_size_int else ""
        bullets.append(f"Crew: {group_type}{size_suffix}")
    elif group_size_int:
        bullets.append(f"Crew size: x{group_size_int}")

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

    saved_payloads: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()
    for payload in state.get("saved_inspirations", []):
        if not isinstance(payload, Mapping):
            continue
        card_id = str(payload.get("id") or payload.get("title") or "").strip()
        if not card_id or card_id in seen_ids:
            continue
        entry = dict(payload)
        entry.setdefault("id", card_id)
        saved_payloads.append(entry)
        seen_ids.add(card_id)

    liked_payloads: List[Dict[str, Any]] = []
    for payload in state.get("liked_inspirations", []):
        if not isinstance(payload, Mapping):
            continue
        card_id = str(payload.get("id") or payload.get("title") or "").strip()
        if not card_id or card_id in seen_ids:
            continue
        entry = dict(payload)
        entry.setdefault("id", card_id)
        liked_payloads.append(entry)
        seen_ids.add(card_id)

    for payload in saved_payloads + liked_payloads:
        category = payload.get("category")
        if category:
            interests_set.add(str(category))

    for payload in saved_payloads:
        title = payload.get("title")
        if title:
            interests_set.add(str(title))

    notes_segments: List[str] = []
    if state.get("flexible_months"):
        months = ", ".join(
            date.fromisoformat(month).strftime("%B %Y")
            for month in state["flexible_months"]
        )
        notes_segments.append(f"Flexible timing: {months}")

    timing_note = str(state.get("timing_note", "")).strip()
    if timing_note:
        notes_segments.append(f"Timing note: {timing_note}")

    group_type = state.get("group_type")
    group_size_int = _coerce_positive_int(state.get("group_size"))
    if group_type:
        size_note = f" ({group_size_int} travellers)" if group_size_int else ""
        notes_segments.append(f"Group: {group_type}{size_note}")
    elif group_size_int:
        notes_segments.append(f"Group size: {group_size_int} travellers")

    if state.get("personal_events"):
        notes_segments.append(
            "Personal additions: " + "; ".join(state["personal_events"])
        )

    existing_notes = str(state.get("notes", "")).strip()
    if existing_notes:
        notes_segments.append(existing_notes)

    combined_notes = "\n".join(notes_segments) if notes_segments else None

    must_do = sorted(
        {
            str(item.get("title") or item.get("id"))
            for item in saved_payloads
            if isinstance(item, dict) and (item.get("title") or item.get("id"))
        }
    )

    return TripIntent(
        destination=destination,
        start_date=start_date if isinstance(start_date, date) else None,
        end_date=end_date if isinstance(end_date, date) else None,
        duration_days=duration_days,
        travel_pace=str(state.get("travel_pace")) if state.get("travel_pace") else None,
        budget=str(state.get("budget")) if state.get("budget") else None,
        mood=str(state.get("mood")) if state.get("mood") else None,
        interests=sorted(interests_set),
        must_do=must_do,
        notes=combined_notes,
        saved_inspirations=saved_payloads,
        liked_inspirations=liked_payloads,
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

    _sync_activity_preferences(state)

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
        body_area = st.container()

        scene = str(state.get("scene") or "conversation")

        if scene not in {"conversation", "interests", "review", "welcome"}:
            scene = "conversation"
            state["scene"] = scene

        if scene == "welcome":
            _render_cinematic_intro(body_area, state)
            if body_area.button("Return to conversation", key="plan_intro_to_conversation", type="primary"):
                state["scene"] = "conversation"
                st.rerun()
        elif scene == "conversation":
            _render_conversation(body_area, state)
        elif scene == "interests":
            _render_interest_gallery(body_area, state)
        else:
            _render_review(body_area, state)
