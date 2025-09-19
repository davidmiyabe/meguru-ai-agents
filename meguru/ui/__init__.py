"""Meguru Streamlit UI helpers."""

from __future__ import annotations

from typing import Any, Callable

from .itinerary import SELECTED_SLOT_KEY, render_itinerary_tab
from .map import render_map_tab
from .plan import ensure_plan_state, render_plan_tab

try:
    from .profile import (
        PROFILE_LOCAL_STORE_KEY,
        PROFILE_STATUS_KEY,
        SUPABASE_SESSION_KEY,
        SUPABASE_TOKENS_KEY,
        render_profile_tab as _render_profile_tab,
        save_trip_to_profile,
    )
except Exception as exc:  # pragma: no cover - exercised via fallback test
    _PROFILE_IMPORT_ERROR = exc

    PROFILE_LOCAL_STORE_KEY = "_profile_local_store"
    PROFILE_STATUS_KEY = "_profile_status"
    SUPABASE_SESSION_KEY = "_supabase_session"
    SUPABASE_TOKENS_KEY = "_supabase_tokens"
    save_trip_to_profile: Callable[..., Any] | None = None

    def render_profile_tab(container: Any) -> None:
        """Fallback profile tab renderer when the full profile module fails to load."""

        import streamlit as st

        with container:
            st.subheader("Profile")
            st.info(
                "Profile features are temporarily unavailable. "
                "Check the application logs for details: "
                f"{_PROFILE_IMPORT_ERROR}"
            )

else:
    render_profile_tab = _render_profile_tab

__all__ = [
    "ensure_plan_state",
    "render_plan_tab",
    "render_itinerary_tab",
    "render_map_tab",
    "render_profile_tab",
    "SELECTED_SLOT_KEY",
    "save_trip_to_profile",
    "PROFILE_LOCAL_STORE_KEY",
    "PROFILE_STATUS_KEY",
    "SUPABASE_SESSION_KEY",
    "SUPABASE_TOKENS_KEY",
]
