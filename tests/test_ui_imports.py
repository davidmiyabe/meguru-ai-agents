"""Sanity checks for the meguru.ui package exports."""

from __future__ import annotations

def _is_callable(value: object) -> bool:
    return callable(value)


def test_tab_renderers_are_exposed() -> None:
    from meguru import ui

    assert _is_callable(ui.render_plan_tab)
    assert _is_callable(ui.render_itinerary_tab)
    assert _is_callable(ui.render_map_tab)
    assert _is_callable(ui.render_profile_tab)


def test_ensure_plan_state_is_available() -> None:
    from meguru import ui

    assert _is_callable(ui.ensure_plan_state)
