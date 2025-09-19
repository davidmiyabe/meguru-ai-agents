"""UI helpers for exploring and refining generated itineraries."""

from __future__ import annotations

from datetime import time
from typing import Dict, List, Tuple

import streamlit as st

from meguru.agents.refiner import RefinerAgent
from meguru.core.exporters import itinerary_to_ics, itinerary_to_pdf
from meguru.core.supabase_api import SupabaseClient
from meguru.schemas import DayPlan, Itinerary, ItineraryEvent, RefinerRequest, TripIntent
from meguru.ui.plan import _ITINERARY_KEY, _PIPELINE_ERROR_KEY, _TRIP_INTENT_KEY
from meguru.ui.profile import (
    SUPABASE_SESSION_KEY,
    SUPABASE_TOKENS_KEY,
    save_trip_to_profile,
)

_SWAP_CONTEXT_KEY = "_itinerary_swap_context"
_SWAP_FEEDBACK_KEY = "_itinerary_swap_feedback"
_SWAP_CONSTRAINTS_KEY = "_itinerary_swap_constraints"
_SWAP_SUCCESS_KEY = "_itinerary_swap_success"
_VIEW_STATE_KEY = "_itinerary_view_mode"
SELECTED_SLOT_KEY = "_itinerary_selected_slot"

_SCHEDULE_SLOTS: Tuple[str, ...] = (
    "Morning",
    "Lunch",
    "Afternoon",
    "Dinner",
    "Evening",
)

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
    start = _format_time(event.start_time)
    end = _format_time(event.end_time)
    if start and end:
        return f"{start}–{end}"
    if start:
        return start
    if end:
        return end
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


def _event_secondary_lines(event: ItineraryEvent) -> List[str]:
    lines: List[str] = []
    if event.place and event.place.formatted_address:
        lines.append(event.place.formatted_address)
    if event.description:
        lines.append(event.description)
    return lines


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


def _render_list_event(day_index: int, event_index: int, event: ItineraryEvent) -> None:
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
            time_range = _format_time_range(event)
            header = f"**{primary}**"
            if time_range:
                header += f" · {time_range}"
            st.markdown(header)
            for line in _event_secondary_lines(event):
                st.caption(line)
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
    time_range = _format_time_range(event)
    body = f"**{primary}**"
    if time_range:
        body += f" · {time_range}"
    column.markdown(body)
    for line in _event_secondary_lines(event):
        column.caption(line)
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
                st.caption(day.summary)
            if not day.events:
                st.info("No activities planned for this day yet.")
            for event_index, event in enumerate(day.events):
                _render_list_event(day_index, event_index, event)


def _render_schedule_view(itinerary: Itinerary) -> None:
    for day_index, day in enumerate(itinerary.days):
        st.markdown(f"#### {_day_label(day)}")
        if day.summary:
            st.caption(day.summary)

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
    st.experimental_rerun()


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
        time_range = _format_time_range(event)
        context_line = f"Currently scheduled: **{primary}**"
        if time_range:
            context_line += f" · {time_range}"
        st.write(context_line)
        for line in _event_secondary_lines(event):
            st.caption(line)

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
            st.experimental_rerun()
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
        save_clicked = action_cols[0].button(
            "Save to profile",
            key="itinerary_save_profile",
            help=save_help,
            use_container_width=True,
        )
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

        if save_clicked:
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

