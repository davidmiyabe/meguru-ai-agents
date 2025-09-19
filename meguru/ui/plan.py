"""UI helpers for the trip planning wizard."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Dict, List, Tuple

import streamlit as st

from meguru.schemas import TripIntent
from meguru.workflows.trip_pipeline import run_trip_pipeline

_WIZARD_KEY = "_plan_wizard_state"
_TRIP_INTENT_KEY = "trip_intent"
_ITINERARY_KEY = "itinerary"
_PIPELINE_ERROR_KEY = "pipeline_error"

_GROUP_TYPES = ["Solo", "Couple", "Family", "Friends", "Colleagues"]
_PACE_OPTIONS = ["Chill", "Balanced", "Packed"]
_BUDGET_OPTIONS = ["Shoestring", "Moderate", "Splurge"]
_INTEREST_PRESETS = [
    "Food", "Culture", "History", "Nature", "Nightlife",
    "Art", "Wellness", "Shopping", "Adventure", "Family-friendly",
]
_STEP_TITLES = [
    "Destinations",
    "Travel dates",
    "Group",
    "Style",
    "Interests",
    "Notes",
]


_LOGGER = logging.getLogger(__name__)


def ensure_plan_state() -> None:
    """Initialise the Streamlit session state used by the planner UI."""

    if _WIZARD_KEY not in st.session_state:
        st.session_state[_WIZARD_KEY] = {
            "step_index": 0,
            "destinations": [],
            "date_mode": "dates",
            "start_date": None,
            "end_date": None,
            "candidate_months": [],
            "group_type": _GROUP_TYPES[1],
            "group_size": 2,
            "pace": _PACE_OPTIONS[1],
            "budget": _BUDGET_OPTIONS[1],
            "interests": [],
            "notes": "",
        }

    st.session_state.setdefault(_TRIP_INTENT_KEY, None)
    st.session_state.setdefault(_ITINERARY_KEY, None)
    st.session_state.setdefault(_PIPELINE_ERROR_KEY, None)
    st.session_state.setdefault("plan_destination_entry_should_reset", False)


def _wizard_state() -> Dict[str, object]:
    return st.session_state[_WIZARD_KEY]


def _handle_add_destination() -> None:
    """Add a destination from the current text input to the wizard state."""

    entry = st.session_state.get("plan_destination_entry", "")
    cleaned = entry.strip()
    wizard_state = _wizard_state()
    if cleaned and cleaned not in wizard_state["destinations"]:
        wizard_state["destinations"].append(cleaned)
    st.session_state["plan_destination_entry_should_reset"] = True


def _render_stepper(container, current_step: int) -> None:
    """Show a simple stepper indicator."""

    columns = container.columns(len(_STEP_TITLES), gap="small")
    for idx, (col, title) in enumerate(zip(columns, _STEP_TITLES)):
        if idx < current_step:
            badge = "✅"
        elif idx == current_step:
            badge = "🟦"
        else:
            badge = "⬜"
        col.markdown(f"{badge} **{title}**")


def _render_destinations_step(container, state: Dict[str, object]) -> None:
    container.subheader("Where are you headed?")
    if st.session_state.get("plan_destination_entry_should_reset"):
        st.session_state["plan_destination_entry"] = ""
        st.session_state["plan_destination_entry_should_reset"] = False
    entry = container.text_input(
        "Add a destination",
        key="plan_destination_entry",
        placeholder="e.g. Kyoto",
    )
    container.button(
        "Add destination",
        key="plan_destination_add",
        use_container_width=True,
        on_click=_handle_add_destination,
    )

    if state["destinations"]:
        container.markdown("**Selected destinations**")
        chips = container.columns(min(4, len(state["destinations"])) or 1)
        for idx, destination in enumerate(list(state["destinations"])):
            target_column = chips[idx % len(chips)]
            if target_column.button(f"❌ {destination}", key=f"plan_destination_remove_{idx}"):
                state["destinations"].remove(destination)

    container.caption("You can add multiple destinations; the first one is treated as primary.")


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


def _render_dates_step(container, state: Dict[str, object]) -> None:
    container.subheader("When do you plan to travel?")
    mode = container.radio(
        "",
        options=("Specific dates", "Flexible months"),
        index=0 if state["date_mode"] == "dates" else 1,
        horizontal=True,
        key="plan_date_mode",
        label_visibility="collapsed",
    )

    if mode == "Specific dates":
        state["date_mode"] = "dates"
        today = date.today()
        default_start = state["start_date"] or today + timedelta(days=14)
        default_end = state["end_date"] or default_start + timedelta(days=6)
        start_date, end_date = container.date_input(
            "Travel dates",
            value=(default_start, default_end),
            min_value=today,
            key="plan_date_range",
        )
        state["start_date"], state["end_date"] = start_date, end_date
        state["candidate_months"] = []
    else:
        state["date_mode"] = "months"
        iso_values, labels = _month_options()
        default_labels = [labels[value] for value in state["candidate_months"] if value in labels]
        selected = container.multiselect(
            "Select candidate months",
            options=[labels[value] for value in iso_values],
            default=default_labels,
            key="plan_months",
        )
        reverse_lookup = {label: iso for iso, label in labels.items()}
        state["candidate_months"] = [reverse_lookup[label] for label in selected]
        state["start_date"] = None
        state["end_date"] = None


def _render_group_step(container, state: Dict[str, object]) -> None:
    container.subheader("Who is coming along?")
    type_index = (
        _GROUP_TYPES.index(state["group_type"])
        if state["group_type"] in _GROUP_TYPES
        else 0
    )
    group_type = container.selectbox(
        "Group type",
        options=_GROUP_TYPES,
        index=type_index,
        key="plan_group_type",
    )
    group_size = container.slider(
        "Group size",
        min_value=1,
        max_value=12,
        value=int(state["group_size"]),
        key="plan_group_size",
    )
    state["group_type"] = group_type
    state["group_size"] = group_size


def _render_style_step(container, state: Dict[str, object]) -> None:
    container.subheader("What travel style do you prefer?")
    pace_index = _PACE_OPTIONS.index(state["pace"]) if state["pace"] in _PACE_OPTIONS else 1
    budget_index = (
        _BUDGET_OPTIONS.index(state["budget"])
        if state["budget"] in _BUDGET_OPTIONS
        else 1
    )
    pace = container.selectbox(
        "Pace",
        options=_PACE_OPTIONS,
        index=pace_index,
        key="plan_pace",
    )
    budget = container.selectbox(
        "Budget",
        options=_BUDGET_OPTIONS,
        index=budget_index,
        key="plan_budget",
    )
    state["pace"] = pace
    state["budget"] = budget


def _render_interests_step(container, state: Dict[str, object]) -> None:
    container.subheader("Interests")
    available_options = sorted(set(_INTEREST_PRESETS) | set(state["interests"]))
    selected = container.multiselect(
        "What excites you?",
        options=available_options,
        default=state["interests"],
        key="plan_interests",
    )
    state["interests"] = selected

    custom_interest = container.text_input(
        "Add another interest",
        key="plan_interest_entry",
        placeholder="e.g. coffee shops",
    )
    if container.button("Add interest", key="plan_interest_add", use_container_width=True):
        cleaned = custom_interest.strip()
        if cleaned and cleaned not in state["interests"]:
            state["interests"].append(cleaned)
        st.session_state["plan_interest_entry"] = ""


def _render_notes_step(container, state: Dict[str, object]) -> None:
    container.subheader("Anything else we should know?")
    notes = container.text_area(
        "Notes",
        key="plan_notes",
        value=state["notes"],
        height=160,
    )
    state["notes"] = notes


_STEP_RENDERERS = [
    _render_destinations_step,
    _render_dates_step,
    _render_group_step,
    _render_style_step,
    _render_interests_step,
    _render_notes_step,
]


def _validate_step(step_index: int, state: Dict[str, object]) -> str | None:
    if step_index == 0 and not state["destinations"]:
        return "Add at least one destination to continue."
    return None


def _build_trip_intent(state: Dict[str, object]) -> TripIntent:
    destinations: List[str] = list(state["destinations"])
    primary_destination = destinations[0]

    notes_segments: List[str] = []
    if len(destinations) > 1:
        notes_segments.append(
            "Additional destinations: " + ", ".join(destinations[1:])
        )

    if state["date_mode"] == "months" and state["candidate_months"]:
        readable_months = ", ".join(
            date.fromisoformat(month).strftime("%B %Y") for month in state["candidate_months"]
        )
        notes_segments.append(f"Flexible timing: {readable_months}")

    group_type = state["group_type"]
    group_size = state["group_size"]
    notes_segments.append(f"Group: {group_type} ({group_size} travellers)")

    existing_notes = state.get("notes") or ""
    if existing_notes.strip():
        notes_segments.append(existing_notes.strip())

    combined_notes = "\n".join(notes_segments) if notes_segments else None

    start_date = state.get("start_date")
    end_date = state.get("end_date")
    duration_days = None
    if isinstance(start_date, date) and isinstance(end_date, date) and end_date >= start_date:
        duration_days = (end_date - start_date).days + 1

    return TripIntent(
        destination=primary_destination,
        start_date=start_date if isinstance(start_date, date) else None,
        end_date=end_date if isinstance(end_date, date) else None,
        duration_days=duration_days,
        travel_pace=state.get("pace"),
        budget=state.get("budget"),
        interests=list(state.get("interests", [])),
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
        return f"{base_message} {details}"
    return f"{base_message} Check your configuration and try again."


def _handle_submit(state: Dict[str, object]) -> None:
    itinerary_placeholder = st.session_state[_ITINERARY_KEY]
    intent = _build_trip_intent(state)
    st.session_state[_TRIP_INTENT_KEY] = intent
    try:
        with st.spinner("Generating your itinerary..."):
            itinerary = run_trip_pipeline(intent)
    except Exception as exc:  # noqa: BLE001 - surfaced to the user
        friendly_message = _format_pipeline_error(exc)
        _LOGGER.exception("Trip pipeline failed")
        st.session_state[_PIPELINE_ERROR_KEY] = friendly_message
        st.session_state[_ITINERARY_KEY] = itinerary_placeholder
        st.error(friendly_message)
    else:
        st.session_state[_PIPELINE_ERROR_KEY] = None
        st.session_state[_ITINERARY_KEY] = itinerary
        st.session_state["_focus_itinerary"] = True
        state["step_index"] = 0
        st.success("Itinerary ready! Check the Itinerary tab for details.")


def render_plan_tab(container) -> None:
    """Render the plan wizard inside the provided container."""

    state = _wizard_state()

    with container:
        st.subheader("Trip planner")
        _render_stepper(st, state["step_index"])  # type: ignore[arg-type]

        current_step = int(state["step_index"])
        _STEP_RENDERERS[current_step](st, state)  # type: ignore[arg-type]

        nav_cols = st.columns([1, 1, 6])
        prev_col, next_col, _ = nav_cols

        if prev_col.button("Back", disabled=current_step == 0, key="plan_nav_back"):
            state["step_index"] = max(0, current_step - 1)

        if current_step < len(_STEP_RENDERERS) - 1:
            next_clicked = next_col.button("Next", type="primary", key="plan_nav_next")
            if next_clicked:
                error = _validate_step(current_step, state)
                if error:
                    st.warning(error)
                else:
                    state["step_index"] = min(len(_STEP_RENDERERS) - 1, current_step + 1)
        else:
            submit_clicked = next_col.button(
                "Generate itinerary",
                type="primary",
                key="plan_submit",
            )
            if submit_clicked:
                error = _validate_step(0, state)
                if error:
                    st.warning(error)
                else:
                    _handle_submit(state)
