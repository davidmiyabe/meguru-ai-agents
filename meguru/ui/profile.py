"""Profile tab UI with Supabase persistence and exports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import streamlit as st

from meguru.core.db import connection_ctx, ensure_application_tables
from meguru.core.exporters import itinerary_to_ics, itinerary_to_pdf
from meguru.core.profile_store import (
    InMemoryProfileStore,
    StoredTrip,
    SupabaseProfileStore,
)
from meguru.core.supabase_api import SupabaseClient, SupabaseError, SupabaseSession
from meguru.schemas import Itinerary, TripIntent


SUPABASE_SESSION_KEY = "_supabase_session"
SUPABASE_TOKENS_KEY = "_supabase_tokens"
PROFILE_LOCAL_STORE_KEY = "_profile_local_store"
PROFILE_STATUS_KEY = "_profile_status"
PROFILE_SCHEMA_READY_KEY = "_profile_schema_ready"


@dataclass(slots=True)
class StoreContext:
    store: InMemoryProfileStore | SupabaseProfileStore
    client: Optional[SupabaseClient]
    session: Optional[SupabaseSession]
    using_supabase: bool


def _get_local_store() -> InMemoryProfileStore:
    store = st.session_state.get(PROFILE_LOCAL_STORE_KEY)
    if not isinstance(store, InMemoryProfileStore):
        store = InMemoryProfileStore(user_id="local-user")
        st.session_state[PROFILE_LOCAL_STORE_KEY] = store
    return store


def _resolve_store() -> StoreContext:
    client = SupabaseClient.from_env()
    local_store = _get_local_store()
    if not client:
        return StoreContext(local_store, None, None, False)

    session = st.session_state.get(SUPABASE_SESSION_KEY)
    if isinstance(session, SupabaseSession) and not session.is_expired():
        return StoreContext(SupabaseProfileStore(client, session), client, session, True)

    tokens = st.session_state.get(SUPABASE_TOKENS_KEY)
    if tokens and isinstance(tokens, dict):
        refresh_token = tokens.get("refresh_token")
        if refresh_token:
            try:
                refreshed = client.refresh_session(refresh_token)
            except SupabaseError as exc:
                st.warning(f"Supabase session refresh failed: {exc}")
                st.session_state.pop(SUPABASE_TOKENS_KEY, None)
                st.session_state.pop(SUPABASE_SESSION_KEY, None)
            else:
                st.session_state[SUPABASE_SESSION_KEY] = refreshed
                st.session_state[SUPABASE_TOKENS_KEY] = {
                    "access_token": refreshed.access_token,
                    "refresh_token": refreshed.refresh_token,
                    "expires_at": refreshed.expires_at,
                }
                return StoreContext(SupabaseProfileStore(client, refreshed), client, refreshed, True)

    return StoreContext(local_store, client, None, False)


def _ensure_schema() -> None:
    if st.session_state.get(PROFILE_SCHEMA_READY_KEY):
        return
    try:
        with connection_ctx() as connection:
            ensure_application_tables(connection)
    except Exception as exc:  # noqa: BLE001 - surfaced to user
        st.warning(f"Unable to validate Supabase tables: {exc}")
        st.session_state[PROFILE_SCHEMA_READY_KEY] = False
    else:
        st.session_state[PROFILE_SCHEMA_READY_KEY] = True


def _render_auth_controls(client: SupabaseClient) -> None:
    st.markdown("#### Supabase account")
    with st.form("profile_auth_form", clear_on_submit=False):
        email = st.text_input("Email", key="profile_auth_email")
        password = st.text_input("Password", type="password", key="profile_auth_password")
        submit_col, register_col = st.columns(2)
        sign_in_clicked = submit_col.form_submit_button("Sign in", use_container_width=True)
        register_clicked = register_col.form_submit_button("Register", use_container_width=True)
        if sign_in_clicked or register_clicked:
            if not email or not password:
                st.warning("Enter both email and password.")
            else:
                try:
                    if register_clicked:
                        session = client.sign_up_with_password(email, password)
                    else:
                        session = client.sign_in_with_password(email, password)
                except SupabaseError as exc:
                    st.error(f"Authentication failed: {exc}")
                else:
                    st.session_state[SUPABASE_SESSION_KEY] = session
                    st.session_state[SUPABASE_TOKENS_KEY] = {
                        "access_token": session.access_token,
                        "refresh_token": session.refresh_token,
                        "expires_at": session.expires_at,
                    }
                    st.session_state[PROFILE_STATUS_KEY] = "Signed in successfully."
                    st.experimental_rerun()


def _render_user_summary(session: SupabaseSession) -> None:
    user = session.user
    st.write(
        f"Signed in as **{user.email or user.id}**",  # noqa: E501 - Markdown formatting for clarity
    )
    sign_out = st.button("Sign out", key="profile_sign_out")
    if sign_out:
        st.session_state.pop(SUPABASE_SESSION_KEY, None)
        st.session_state.pop(SUPABASE_TOKENS_KEY, None)
        st.session_state[PROFILE_STATUS_KEY] = "Signed out."
        st.experimental_rerun()


def _load_trips(store: InMemoryProfileStore | SupabaseProfileStore) -> List[StoredTrip]:
    try:
        return store.list_trips()
    except SupabaseError as exc:
        st.error(f"Unable to load trips: {exc}")
        return []


def _render_trip_summary(trip: StoredTrip, store: InMemoryProfileStore | SupabaseProfileStore) -> None:
    with st.expander(trip.name, expanded=False):
        if trip.start_date and trip.end_date:
            st.caption(
                f"{trip.start_date.strftime('%b %d, %Y')} – {trip.end_date.strftime('%b %d, %Y')}"
            )
        if trip.intent.interests:
            st.caption("Interests: " + ", ".join(trip.intent.interests))

        action_cols = st.columns(3)
        duplicate_clicked = action_cols[0].button(
            "Duplicate",
            key=f"profile_duplicate_{trip.id}",
            use_container_width=True,
        )
        ics_data = itinerary_to_ics(trip.itinerary, calendar_name=trip.name)
        action_cols[1].download_button(
            "Download ICS",
            data=ics_data,
            file_name=f"{trip.name}.ics",
            mime="text/calendar",
            key=f"profile_download_ics_{trip.id}",
            use_container_width=True,
        )
        pdf_data = itinerary_to_pdf(trip.itinerary)
        action_cols[2].download_button(
            "Download PDF",
            data=pdf_data,
            file_name=f"{trip.name}.pdf",
            mime="application/pdf",
            key=f"profile_download_pdf_{trip.id}",
            use_container_width=True,
        )

        if duplicate_clicked:
            try:
                duplicate = store.duplicate_trip(trip.id)
            except SupabaseError as exc:
                st.error(f"Unable to duplicate trip: {exc}")
            except Exception as exc:  # noqa: BLE001 - surface unexpected issues
                st.error(f"Unexpected error duplicating trip: {exc}")
            else:
                if duplicate:
                    st.session_state[PROFILE_STATUS_KEY] = f"Duplicated {trip.name}."
                    st.experimental_rerun()

        st.markdown("### Day by day")
        for day in trip.itinerary.days:
            day_label = day.label or day.date.strftime("%A") if day.date else "Day"
            st.markdown(f"**{day_label}**")
            for event in day.events:
                event_title = event.title or (event.place.name if event.place else "Activity")
                detail_parts: List[str] = []
                if event.start_time:
                    detail_parts.append(event.start_time.strftime("%H:%M"))
                if event.end_time:
                    detail_parts.append(event.end_time.strftime("%H:%M"))
                timing = "–".join(detail_parts)
                header = event_title
                if timing:
                    header += f" ({timing})"
                st.write(f"- {header}")
                if event.description:
                    st.caption(event.description)


def save_trip_to_profile(
    intent: TripIntent,
    itinerary: Itinerary,
    *,
    name: Optional[str] = None,
) -> Tuple[Optional[StoredTrip], Optional[str]]:
    """Persist the supplied trip using the active profile store."""

    context = _resolve_store()
    store = context.store
    if context.using_supabase:
        _ensure_schema()
    try:
        saved = store.save_trip(intent, itinerary, name=name)
    except SupabaseError as exc:
        return None, str(exc)
    except Exception as exc:  # noqa: BLE001 - unexpected runtime failure
        return None, str(exc)
    st.session_state[PROFILE_STATUS_KEY] = f"Saved {saved.name}."
    return saved, None


def render_profile_tab(container) -> None:
    """Render the profile tab with authentication and trip management."""

    context = _resolve_store()
    with container:
        st.subheader("Profile")

        status = st.session_state.pop(PROFILE_STATUS_KEY, None)
        if status:
            st.success(status)

        if context.client is None:
            st.info(
                "Configure `SUPABASE_URL` and `SUPABASE_ANON_KEY` to sync trips to Supabase. "
                "Trips are stored locally for this session."
            )
        elif context.session is None:
            _render_auth_controls(context.client)
        else:
            _ensure_schema()
            _render_user_summary(context.session)

        trips = _load_trips(context.store)
        if not trips:
            st.info("No trips saved yet. Generate an itinerary and save it to see it here.")
            return

        for trip in trips:
            _render_trip_summary(trip, context.store)


__all__ = [
    "PROFILE_LOCAL_STORE_KEY",
    "PROFILE_STATUS_KEY",
    "SUPABASE_SESSION_KEY",
    "SUPABASE_TOKENS_KEY",
    "render_profile_tab",
    "save_trip_to_profile",
]

