"""Streamlit entry point for the Meguru application."""
from __future__ import annotations

from typing import Sequence

import streamlit as st
from dotenv import load_dotenv

from meguru.ui.plan import ensure_plan_state, render_itinerary_tab, render_plan_tab


_TAB_ORDER: Sequence[str] = ("Plan", "Itinerary", "Map", "Profile")


def configure() -> None:
    """Configure global Streamlit settings and load environment variables."""

    load_dotenv()
    st.set_page_config(page_title="Meguru", layout="wide")


def _resolve_tab_order() -> Sequence[str]:
    """Return the ordered list of tab labels for the current render cycle."""

    default_tab = st.session_state.get("app_active_tab", "Plan")
    focus_itinerary = st.session_state.pop("_focus_itinerary", False)
    if focus_itinerary:
        default_tab = "Itinerary"

    if default_tab not in _TAB_ORDER:
        default_tab = "Plan"

    ordered = [default_tab, *[label for label in _TAB_ORDER if label != default_tab]]
    st.session_state["app_active_tab"] = default_tab
    return ordered


def render() -> None:
    """Render the Meguru multi-tab shell."""

    ensure_plan_state()

    st.title("🧭 Meguru")

    ordered_tabs = _resolve_tab_order()
    tab_containers = st.tabs(list(ordered_tabs))
    tab_lookup = {label: container for label, container in zip(ordered_tabs, tab_containers)}

    render_plan_tab(tab_lookup["Plan"])
    render_itinerary_tab(tab_lookup["Itinerary"])

    tab_lookup["Map"].write("Map view coming soon.")
    tab_lookup["Profile"].write("Traveler profile details will live here.")


if __name__ == "__main__":
    configure()
    render()
