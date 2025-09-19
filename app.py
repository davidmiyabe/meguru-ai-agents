"""Streamlit entry point for the Meguru application."""
from __future__ import annotations

import streamlit as st
from dotenv import load_dotenv


def configure() -> None:
    """Configure global Streamlit settings and load environment variables."""
    load_dotenv()
    st.set_page_config(page_title="Meguru", layout="wide")


def render() -> None:
    """Render the Meguru multi-tab shell."""
    st.title("🧭 Meguru")
    plan_tab, itinerary_tab, map_tab, profile_tab = st.tabs(
        [
            "Plan",
            "Itinerary",
            "Map",
            "Profile",
        ]
    )

    with plan_tab:
        st.write("Plan your adventure here.")

    with itinerary_tab:
        st.write("Your itinerary will appear here.")

    with map_tab:
        st.write("Map view coming soon.")

    with profile_tab:
        st.write("Traveler profile details will live here.")


if __name__ == "__main__":
    configure()
    render()
