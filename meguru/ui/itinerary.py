"""UI helpers for exploring and refining generated itineraries."""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from typing import Any, Dict, Iterable, List, Mapping, Tuple

import streamlit as st

from meguru.agents.refiner import RefinerAgent
from meguru.core.exporters import itinerary_to_ics, itinerary_to_pdf
from meguru.core.supabase_api import SupabaseClient
from meguru.schemas import DayPlan, Itinerary, ItineraryEvent, RefinerRequest, TripIntent
from meguru.ui.plan import _ITINERARY_KEY, _PIPELINE_ERROR_KEY, _TRIP_INTENT_KEY

_LOGGER = logging.getLogger(__name__)

_PROFILE_IMPORT_ERROR: Exception | None = None
_PROFILE_FALLBACK_MESSAGE: str | None = None

try:
    from meguru.ui.profile import (
        SUPABASE_SESSION_KEY,
        SUPABASE_TOKENS_KEY,
        save_trip_to_profile,
    )
except Exception as exc:  # pragma: no cover - exercised via targeted tests
    _PROFILE_IMPORT_ERROR = exc
    _PROFILE_FALLBACK_MESSAGE = (
        "Profile features are temporarily unavailable. "
        "Check the application logs for details: "
        f"{exc}"
    )
    _LOGGER.warning("Profile module failed to import: %s", exc)

    SUPABASE_SESSION_KEY = "_supabase_session"
    SUPABASE_TOKENS_KEY = "_supabase_tokens"
    save_trip_to_profile = None
else:  # pragma: no cover - exercised when profile imports correctly
    _PROFILE_FALLBACK_MESSAGE = None

_SWAP_CONTEXT_KEY = "_itinerary_swap_context"
_SWAP_FEEDBACK_KEY = "_itinerary_swap_feedback"
_SWAP_CONSTRAINTS_KEY = "_itinerary_swap_constraints"
_SWAP_SUCCESS_KEY = "_itinerary_swap_success"
_VIEW_STATE_KEY = "_itinerary_view_mode"
SELECTED_SLOT_KEY = "_itinerary_selected_slot"

_CATEGORY_DISPLAY: Tuple[Tuple[str, str, bool], ...] = (
    ("wake_up", "Wake-up", False),
    ("breakfast", "Breakfast", False),
    ("morning_activity", "Morning activity", False),
    ("snack_morning", "Morning snack", True),
    ("lunch", "Lunch", False),
    ("afternoon_activity", "Afternoon activity", False),
    ("snack_afternoon", "Afternoon snack", True),
    ("dinner", "Dinner", False),
    ("evening_activity", "Evening activity", True),
)

_CATEGORY_LABELS = {key: label for key, label, _ in _CATEGORY_DISPLAY}

_SCHEDULE_SLOTS: Tuple[str, ...] = (
    "Morning",
    "Lunch",
    "Afternoon",
    "Dinner",
    "Evening",
)

_CATEGORY_SLOT_OVERRIDES: Dict[str, str] = {
    "wake_up": "Morning",
    "breakfast": "Morning",
    "morning_activity": "Morning",
    "snack_morning": "Morning",
    "lunch": "Lunch",
    "afternoon_activity": "Afternoon",
    "snack_afternoon": "Afternoon",
    "dinner": "Dinner",
    "evening_activity": "Evening",
}

_SLOT_KEYWORDS: Dict[str, str] = {
    "breakfast": "Morning",
    "brunch": "Morning",
    "coffee": "Morning",
    "sunrise": "Morning",
    "lunch": "Lunch",
    "midday": "Lunch",
    "afternoon": "Afternoon",
    "tea": "Afternoon",
    "museum": "Afternoon",
    "dinner": "Dinner",
    "supper": "Dinner",
    "tasting": "Dinner",
    "evening": "Evening",
    "night": "Evening",
    "drinks": "Evening",
    "bar": "Evening",
    "show": "Evening",
}

_SLOT_TIME_WINDOWS: Tuple[Tuple[str, time, time], ...] = (
    ("Morning", time(6, 0), time(11, 0)),
    ("Lunch", time(11, 0), time(14, 0)),
    ("Afternoon", time(14, 0), time(17, 0)),
    ("Dinner", time(17, 0), time(20, 30)),
    ("Evening", time(20, 30), time(23, 59, 59)),
)

_REFINER_AGENT: RefinerAgent | None = None


def _dedupe_inspirations(cards: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    seen: set[str] = set()
    deduped: List[Dict[str, Any]] = []
    for card in cards:
        if not isinstance(card, Mapping):
            continue
        card_id = str(card.get("id") or card.get("title") or "").strip()
        if not card_id or card_id in seen:
            continue
        payload = dict(card)
        payload.setdefault("id", card_id)
        deduped.append(payload)
        seen.add(card_id)
    return deduped


def _format_inspiration_lines(cards: Iterable[Mapping[str, Any]]) -> str:
    lines: List[str] = []
    for card in _dedupe_inspirations(cards):
        title = str(card.get("title") or card.get("id") or "Experience")
        category = str(card.get("category") or "").strip()
        location_hint = str(card.get("location_hint") or "").strip()
        descriptor = f"**{title}**"
        if category:
            descriptor += f" · {category}"
        if location_hint:
            descriptor += f" — {location_hint}"
        lines.append(f"- {descriptor}")
    return "\n".join(lines)


def _ensure_session_state() -> None:
    st.session_state.setdefault(_SWAP_CONTEXT_KEY, None)
    st.session_state.setdefault(_SWAP_FEEDBACK_KEY, "")
    st.session_state.setdefault(_SWAP_CONSTRAINTS_KEY, "")
    st.session_state.setdefault(_VIEW_STATE_KEY, "List")
    st.session_state.setdefault(SELECTED_SLOT_KEY, None)


def _get_refiner_agent() -> RefinerAgent:
    global _REFINER_AGENT
    if _REFINER_AGENT is None:
        _REFINER_AGENT = RefinerAgent()
    return _REFINER_AGENT


def _format_time(value: time | None) -> str:
    if not value:
        return ""
    return value.strftime("%H:%M")


def _format_time_range(event: ItineraryEvent) -> str:
    computed_end: time | None = event.end_time
    if (
        event.start_time
        and not computed_end
        and event.duration_minutes is not None
        and event.duration_minutes > 0
    ):
        base = datetime.combine(datetime.today().date(), event.start_time)
        computed_end = (base + timedelta(minutes=event.duration_minutes)).time()

    start = _format_time(event.start_time)
    end = _format_time(computed_end)
    if start and end:
        return f"{start}–{end}"
    if start:
        if event.duration_minutes:
            return f"{start} · {event.duration_minutes} min"
        return start
    if end:
        return end
    if event.duration_minutes:
        return f"~{event.duration_minutes} min"
    return ""


def _day_label(day: DayPlan) -> str:
    if day.label:
        return day.label
    if day.date:
        return day.date.strftime("%A, %b %d")
    return "Day"


def _event_primary_label(event: ItineraryEvent) -> str:
    if event.place and event.place.name:
        return event.place.name
    return event.title


def _event_detail_pairs(event: ItineraryEvent) -> List[Tuple[str, str]]:
    details: List[Tuple[str, str]] = []

    time_range = _format_time_range(event)
    if time_range:
        details.append(("Time", time_range))

    if event.duration_minutes and (not time_range or "·" not in time_range):
        details.append(("Estimated duration", f"{event.duration_minutes} min"))

    location_parts: List[str] = []
    if event.location:
        location_parts.append(event.location)

    if event.place and event.place.formatted_address:
        location_parts.append(event.place.formatted_address)
    if location_parts:
        joined_location = " · ".join(dict.fromkeys(location_parts))
        details.append(("Location", joined_location))

    if event.description:
        details.append(("Details", event.description))

    if event.justification:
        details.append(("Why", event.justification))

    if event.tags:
        details.append(("Tags", ", ".join(event.tags)))

    return details


def _open_swap(day_index: int, event_index: int) -> None:
    st.session_state[_SWAP_CONTEXT_KEY] = {
        "day_index": day_index,
        "event_index": event_index,
    }
    st.session_state[_SWAP_FEEDBACK_KEY] = ""
    st.session_state[_SWAP_CONSTRAINTS_KEY] = ""


def _close_swap() -> None:
    st.session_state[_SWAP_CONTEXT_KEY] = None
    st.session_state[_SWAP_FEEDBACK_KEY] = ""
    st.session_state[_SWAP_CONSTRAINTS_KEY] = ""


def _infer_schedule_slot(event: ItineraryEvent, fallback_index: int) -> str:
    if event.category and event.category in _CATEGORY_SLOT_OVERRIDES:
        return _CATEGORY_SLOT_OVERRIDES[event.category]
    if event.start_time:
        start_time = event.start_time
        for slot_name, window_start, window_end in _SLOT_TIME_WINDOWS:
            if window_start <= start_time <= window_end:
                return slot_name

    haystack_parts = [
        event.title or "",
        event.description or "",
        " ".join(event.tags or []),
    ]
    if event.place and event.place.name:
        haystack_parts.append(event.place.name)
    haystack = " ".join(part.lower() for part in haystack_parts if part)

    for keyword, slot in _SLOT_KEYWORDS.items():
        if keyword in haystack:
            return slot

    return _SCHEDULE_SLOTS[fallback_index % len(_SCHEDULE_SLOTS)]


def _build_schedule(day: DayPlan) -> Dict[str, List[Tuple[int, ItineraryEvent]]]:
    buckets: Dict[str, List[Tuple[int, ItineraryEvent]]] = {
        slot: [] for slot in _SCHEDULE_SLOTS
    }
    for idx, event in enumerate(day.events):
        slot = _infer_schedule_slot(event, idx)
        buckets.setdefault(slot, []).append((idx, event))
    return buckets


def _render_list_event(
    day_index: int,
    event_index: int,
    event: ItineraryEvent,
    *,
    slot_label: str | None = None,
) -> None:
    selected_slot = st.session_state.get(SELECTED_SLOT_KEY)
    is_selected = selected_slot == (day_index, event_index)

    highlight_start = ""
    highlight_end = ""
    if is_selected:
        highlight_start = (
            "<div style=\"background-color:#eef2ff;border-left:4px solid "
            "#3b82f6;padding:0.75rem;border-radius:0.5rem;\">"
        )
        highlight_end = "</div>"

    container = st.container()
    with container:
        if highlight_start:
            st.markdown(highlight_start, unsafe_allow_html=True)

        details_col, action_col = st.columns([4, 1])
        with details_col:
            primary = _event_primary_label(event)
            if slot_label:
                header = f"**{slot_label}:** {primary}"
            else:
                header = f"**{primary}**"
            st.markdown(header)
            for label, value in _event_detail_pairs(event):
                st.caption(f"**{label}:** {value}")
        action_col.button(
            "Swap this",
            key=f"swap_list_{day_index}_{event_index}",
            on_click=_open_swap,
            args=(day_index, event_index),
            use_container_width=True,
        )

        if highlight_end:
            st.markdown(highlight_end, unsafe_allow_html=True)


def _render_schedule_event(
    column, day_index: int, event_index: int, event: ItineraryEvent
) -> None:
    primary = _event_primary_label(event)
    slot_label = _CATEGORY_LABELS.get(event.category) if event.category else None
    if slot_label:
        body = f"**{slot_label}:** {primary}"
    else:
        body = f"**{primary}**"
    column.markdown(body)
    for label, value in _event_detail_pairs(event):
        column.caption(f"**{label}:** {value}")
    column.button(
        "Swap this",
        key=f"swap_schedule_{day_index}_{event_index}",
        on_click=_open_swap,
        args=(day_index, event_index),
        use_container_width=True,
    )


def _render_list_view(itinerary: Itinerary) -> None:
    for day_index, day in enumerate(itinerary.days):
        label = _day_label(day)
        with st.expander(label, expanded=True):
            if day.summary:
                st.markdown(f"**Theme of the day:** {day.summary}")

            if not day.events:
                st.info("No activities planned for this day yet.")

            events_by_category: Dict[str, List[Tuple[int, ItineraryEvent]]] = {}
            uncategorised: List[Tuple[int, ItineraryEvent]] = []
            for event_index, event in enumerate(day.events):
                if event.category and event.category in _CATEGORY_LABELS:
                    events_by_category.setdefault(event.category, []).append((event_index, event))
                else:
                    uncategorised.append((event_index, event))

            for category, slot_label, is_optional in _CATEGORY_DISPLAY:
                category_events = events_by_category.get(category, [])
                if category_events:
                    for event_index, event in category_events:
                        _render_list_event(
                            day_index,
                            event_index,
                            event,
                            slot_label=slot_label,
                        )
                elif not is_optional:
                    st.caption(f"**{slot_label}:** To be decided.")

            if uncategorised:
                st.markdown("**Additional plans**")
                for event_index, event in uncategorised:
                    _render_list_event(day_index, event_index, event)


def _render_schedule_view(itinerary: Itinerary) -> None:
    for day_index, day in enumerate(itinerary.days):
        st.markdown(f"#### {_day_label(day)}")
        if day.summary:
            st.markdown(f"**Theme of the day:** {day.summary}")

        schedule = _build_schedule(day)
        columns = st.columns(len(_SCHEDULE_SLOTS), gap="medium")
        for slot_name, column in zip(_SCHEDULE_SLOTS, columns):
            column.markdown(f"**{slot_name}**")
            events = schedule.get(slot_name, [])
            if not events:
                column.caption("No plans yet.")
                continue
            for event_index, event in events:
                _render_schedule_event(column, day_index, event_index, event)

        if day_index < len(itinerary.days) - 1:
            st.divider()


def _handle_swap_request(
    itinerary: Itinerary,
    day_index: int,
    event_index: int,
    user_feedback: str,
    constraints: str,
) -> None:
    day = itinerary.days[day_index]
    event = day.events[event_index]

    base_feedback = f"Please replace the activity '{event.title}'."
    extra_feedback = user_feedback.strip()
    if extra_feedback:
        feedback = f"{base_feedback} {extra_feedback}"
    else:
        feedback = f"{base_feedback} Suggest something different."

    constraint_text = constraints.strip() or None

    request = RefinerRequest(
        itinerary=itinerary,
        day_index=day_index,
        feedback=feedback,
        additional_constraints=constraint_text,
    )

    agent = _get_refiner_agent()
    try:
        with st.spinner("Requesting a fresh idea..."):
            response = agent.run(request)
    except Exception as exc:  # noqa: BLE001 - surfaced to the user
        st.error(f"Unable to swap this slot: {exc}")
        return

    st.session_state[_ITINERARY_KEY] = response.itinerary
    updated_day_label = _day_label(response.updated_day)
    success_message = (
        response.notes
        if response.notes
        else f"{updated_day_label} refreshed with a new suggestion."
    )
    st.session_state[_SWAP_SUCCESS_KEY] = success_message
    _close_swap()
    st.rerun()


def _render_swap_modal(itinerary: Itinerary) -> None:
    target = st.session_state.get(_SWAP_CONTEXT_KEY)
    if not target:
        return

    day_index = target.get("day_index")
    event_index = target.get("event_index")
    if day_index is None or event_index is None:
        _close_swap()
        return

    if day_index >= len(itinerary.days):
        _close_swap()
        return

    day = itinerary.days[day_index]
    if event_index >= len(day.events):
        _close_swap()
        return

    event = day.events[event_index]

    with st.modal("Swap itinerary activity"):
        st.markdown(f"### {_day_label(day)}")
        primary = _event_primary_label(event)
        slot_label = _CATEGORY_LABELS.get(event.category) if event.category else None
        if slot_label:
            context_line = f"Currently scheduled: **{slot_label}:** {primary}"
        else:
            context_line = f"Currently scheduled: **{primary}**"
        st.write(context_line)
        for label, value in _event_detail_pairs(event):
            st.caption(f"**{label}:** {value}")

        st.text_area(
            "What would you prefer instead?",
            key=_SWAP_FEEDBACK_KEY,
            placeholder="Tell us the vibe you're after or specific ideas to try.",
            height=120,
        )
        st.text_input(
            "Any must-haves or restrictions?",
            key=_SWAP_CONSTRAINTS_KEY,
            placeholder="Optional notes like budget, cuisine, accessibility, etc.",
        )

        actions = st.columns(2)
        if actions[0].button("Cancel", key="swap_cancel"):
            _close_swap()
            st.rerun()
            return

        if actions[1].button("Request swap", type="primary", key="swap_submit"):
            _handle_swap_request(
                itinerary,
                day_index,
                event_index,
                st.session_state[_SWAP_FEEDBACK_KEY],
                st.session_state[_SWAP_CONSTRAINTS_KEY],
            )


def render_itinerary_tab(container) -> None:
    """Render the itinerary tab content with refinement controls."""

    _ensure_session_state()

    itinerary = st.session_state.get(_ITINERARY_KEY)
    error_message = st.session_state.get(_PIPELINE_ERROR_KEY)
    intent = st.session_state.get(_TRIP_INTENT_KEY)

    with container:
        st.subheader("Itinerary")

        if error_message:
            st.error(error_message)

        if not itinerary:
            st.info("Plan your trip from the Plan tab to generate an itinerary.")
            return

        if _SWAP_SUCCESS_KEY in st.session_state:
            success_message = st.session_state.pop(_SWAP_SUCCESS_KEY, None)
            if success_message:
                st.success(success_message)

        st.markdown(f"### {itinerary.destination}")
        if intent and intent.interests:
            st.caption("Interests: " + ", ".join(intent.interests))

        if intent and (intent.saved_inspirations or intent.liked_inspirations):
            st.markdown("#### Saved inspirations")
            saved_lines = _format_inspiration_lines(intent.saved_inspirations)
            if saved_lines:
                st.markdown(saved_lines)
            else:
                st.caption("Your saved picks will appear here once you add them from the Plan tab.")

            liked_lines = _format_inspiration_lines(intent.liked_inspirations)
            if liked_lines:
                st.markdown("**Liked inspirations**")
                st.markdown(liked_lines)

        if itinerary.start_date and itinerary.end_date:
            start = itinerary.start_date.strftime("%b %d, %Y")
            end = itinerary.end_date.strftime("%b %d, %Y")
            st.write(f"Dates: {start} – {end}")

        if itinerary.notes:
            st.markdown(itinerary.notes, unsafe_allow_html=True)

        action_cols = st.columns(3)
        has_session = bool(st.session_state.get(SUPABASE_SESSION_KEY) or st.session_state.get(SUPABASE_TOKENS_KEY))
        supabase_configured = SupabaseClient.from_env() is not None
        save_help = None
        if supabase_configured and not has_session:
            save_help = "Sign in from the Profile tab to sync this trip with Supabase."
        if save_trip_to_profile:
            save_clicked = action_cols[0].button(
                "Save to profile",
                key="itinerary_save_profile",
                help=save_help,
                use_container_width=True,
            )
        else:
            save_clicked = False
            message = _PROFILE_FALLBACK_MESSAGE or (
                "Profile features are temporarily unavailable. "
                "Check the application logs for details."
            )
            action_cols[0].info(message)
        ics_data = itinerary_to_ics(itinerary, calendar_name=itinerary.destination or "Trip")
        action_cols[1].download_button(
            "Download ICS",
            data=ics_data,
            file_name=f"{(itinerary.destination or 'trip').replace(' ', '_')}.ics",
            mime="text/calendar",
            key="itinerary_download_ics",
            use_container_width=True,
        )
        pdf_data = itinerary_to_pdf(itinerary)
        action_cols[2].download_button(
            "Download PDF",
            data=pdf_data,
            file_name=f"{(itinerary.destination or 'trip').replace(' ', '_')}.pdf",
            mime="application/pdf",
            key="itinerary_download_pdf",
            use_container_width=True,
        )

        if save_clicked and save_trip_to_profile:
            effective_intent = intent or TripIntent(destination=itinerary.destination or "Trip")
            trip_name = itinerary.destination or effective_intent.destination or "Trip"
            saved, error = save_trip_to_profile(effective_intent, itinerary, name=trip_name)
            if error:
                st.error(f"Unable to save trip: {error}")
            elif saved:
                st.success(f"Saved {saved.name} to your profile.")

        view_mode = st.radio(
            "Display",
            options=("List", "Schedule"),
            horizontal=True,
            key=_VIEW_STATE_KEY,
        )

        if view_mode == "Schedule":
            _render_schedule_view(itinerary)
        else:
            _render_list_view(itinerary)

        _render_swap_modal(itinerary)


__all__ = ["render_itinerary_tab", "SELECTED_SLOT_KEY"]

