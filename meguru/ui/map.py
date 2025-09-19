"""Interactive itinerary map view."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import pydeck as pdk
import streamlit as st

from meguru.schemas import DayPlan, Itinerary, ItineraryEvent
from meguru.ui.itinerary import SELECTED_SLOT_KEY
from meguru.ui.plan import _ITINERARY_KEY

_MAP_DAY_FILTER_KEY = "_map_day_filter"
_EVENT_LAYER_ID = "itinerary-events"
_PATH_LAYER_ID = "itinerary-path"

_DAY_COLORS: Sequence[Tuple[int, int, int, int]] = (
    (59, 130, 246, 200),   # blue
    (34, 197, 94, 200),    # green
    (249, 115, 22, 200),   # orange
    (217, 70, 239, 200),   # purple
    (234, 179, 8, 200),    # amber
    (14, 165, 233, 200),   # sky
)

_SELECTED_COLOR: Tuple[int, int, int, int] = (29, 78, 216, 255)


@dataclass
class _Marker:
    position: Tuple[float, float]
    title: str
    subtitle: str
    day_index: int
    event_index: int
    color: Tuple[int, int, int, int]
    radius: int

    def as_dict(self) -> Dict[str, object]:
        longitude, latitude = self.position
        return {
            "id": f"{self.day_index}-{self.event_index}",
            "longitude": longitude,
            "latitude": latitude,
            "color": list(self.color),
            "radius": self.radius,
            "title": self.title,
            "subtitle": self.subtitle,
            "day_index": self.day_index,
            "event_index": self.event_index,
        }


def _day_label(day: DayPlan) -> str:
    if day.label:
        return day.label
    if day.date:
        return day.date.strftime("%A, %b %d")
    return f"Day"


def _format_marker_title(event: ItineraryEvent) -> str:
    if event.place and event.place.name:
        return event.place.name
    return event.title


def _marker_color(day_index: int, selected: bool) -> Tuple[int, int, int, int]:
    if selected:
        return _SELECTED_COLOR
    return _DAY_COLORS[day_index % len(_DAY_COLORS)]


def _collect_markers(itinerary: Itinerary) -> List[_Marker]:
    selected_slot: Optional[Tuple[int, int]] = st.session_state.get(SELECTED_SLOT_KEY)
    markers: List[_Marker] = []
    for day_index, day in enumerate(itinerary.days):
        subtitle = f"Day {day_index + 1}: {_day_label(day)}"
        for event_index, event in enumerate(day.events):
            place = event.place
            if not place or place.latitude is None or place.longitude is None:
                continue
            is_selected = selected_slot == (day_index, event_index)
            color = _marker_color(day_index, is_selected)
            radius = 120 if is_selected else 80
            marker = _Marker(
                position=(place.longitude, place.latitude),
                title=_format_marker_title(event),
                subtitle=subtitle,
                day_index=day_index,
                event_index=event_index,
                color=color,
                radius=radius,
            )
            markers.append(marker)
    return markers


def _collect_paths(itinerary: Itinerary) -> List[Dict[str, object]]:
    paths: List[Dict[str, object]] = []
    for day_index, day in enumerate(itinerary.days):
        path: List[Tuple[float, float]] = []
        for event in day.events:
            place = event.place
            if not place or place.latitude is None or place.longitude is None:
                continue
            path.append((place.longitude, place.latitude))
        if len(path) >= 2:
            color = list(_DAY_COLORS[day_index % len(_DAY_COLORS)])
            path_data = {
                "path": path,
                "color": color,
                "day_index": day_index,
            }
            paths.append(path_data)
    return paths


def _compute_view_state(markers: Sequence[_Marker]) -> pdk.ViewState:
    if not markers:
        return pdk.ViewState(latitude=0, longitude=0, zoom=1)
    avg_lat = sum(marker.position[1] for marker in markers) / len(markers)
    avg_lon = sum(marker.position[0] for marker in markers) / len(markers)
    if len(markers) == 1:
        zoom = 13
    elif len(markers) <= 5:
        zoom = 12
    else:
        zoom = 11
    return pdk.ViewState(latitude=avg_lat, longitude=avg_lon, zoom=zoom)


def _resolve_day_filter_options(itinerary: Itinerary) -> List[Tuple[str, Optional[int]]]:
    options: List[Tuple[str, Optional[int]]] = [("All days", None)]
    for day_index, day in enumerate(itinerary.days):
        options.append((f"Day {day_index + 1}", day_index))
    return options


def _render_day_filter(itinerary: Itinerary) -> Optional[int]:
    options = _resolve_day_filter_options(itinerary)
    option_labels = [label for label, _ in options]
    current = st.session_state.get(_MAP_DAY_FILTER_KEY, options[0][0])
    try:
        current_index = option_labels.index(current)
    except ValueError:
        current_index = 0

    selection = st.radio(
        "Show", option_labels, index=current_index, horizontal=True, key=_MAP_DAY_FILTER_KEY
    )
    selected_value = dict(options).get(selection)
    return selected_value


def _normalise_path_items(paths: List[Dict[str, object]]) -> List[Dict[str, object]]:
    normalised: List[Dict[str, object]] = []
    for item in paths:
        path = item.get("path", [])
        if len(path) < 2:
            continue
        normalised.append(item)
    return normalised


def _build_deck(markers: List[_Marker], paths: List[Dict[str, object]]) -> pdk.Deck:
    marker_dicts = [marker.as_dict() for marker in markers]

    layers = []
    if marker_dicts:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=marker_dicts,
                id=_EVENT_LAYER_ID,
                get_position="[longitude, latitude]",
                get_fill_color="color",
                get_line_color="color",
                get_radius="radius",
                radius_units="meters",
                pickable=True,
                stroked=True,
                auto_highlight=False,
            )
        )

    normalised_paths = _normalise_path_items(paths)
    if normalised_paths:
        layers.append(
            pdk.Layer(
                "PathLayer",
                data=normalised_paths,
                id=_PATH_LAYER_ID,
                get_path="path",
                get_color="color",
                get_width=4,
                width_min_pixels=2,
            )
        )

    tooltip = {
        "html": "<b>{title}</b><br/>{subtitle}",
        "style": {"backgroundColor": "#111", "color": "white"},
    }

    view_state = _compute_view_state(markers)
    deck = pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        layers=layers,
        initial_view_state=view_state,
        tooltip=tooltip,
    )
    return deck


def _update_selection_from_map(state) -> None:
    if not state:
        return
    selection = getattr(state, "selection", None)
    if not selection:
        selection = state.get("selection") if isinstance(state, dict) else None
    if not selection:
        return

    objects = selection.get("objects") if isinstance(selection, dict) else getattr(selection, "objects", None)
    if not objects:
        return

    layer_objects = objects.get(_EVENT_LAYER_ID)
    if not layer_objects:
        return

    first = layer_objects[0]
    selected_obj = first.get("object") if isinstance(first, dict) else None
    if not selected_obj:
        return

    day_index = selected_obj.get("day_index")
    event_index = selected_obj.get("event_index")
    if day_index is None or event_index is None:
        return

    current = st.session_state.get(SELECTED_SLOT_KEY)
    new_value = (day_index, event_index)
    if current != new_value:
        st.session_state[SELECTED_SLOT_KEY] = new_value


def render_map_tab(container) -> None:
    """Render the itinerary map tab."""

    itinerary: Itinerary | None = st.session_state.get(_ITINERARY_KEY)

    with container:
        st.subheader("Map")

        if not itinerary or not itinerary.days:
            st.info("Generate an itinerary to explore it on the map.")
            return

        st.session_state.setdefault(SELECTED_SLOT_KEY, None)

        markers = _collect_markers(itinerary)
        if not markers:
            st.warning("No mappable activities were found. Add places with coordinates to view them here.")
            return

        day_index = _render_day_filter(itinerary)

        filtered_markers = [m for m in markers if day_index is None or m.day_index == day_index]
        if not filtered_markers:
            st.info("No activities for the selected day have map coordinates yet.")
            return

        if day_index is not None:
            valid_slots = {(m.day_index, m.event_index) for m in filtered_markers}
            selected_slot = st.session_state.get(SELECTED_SLOT_KEY)
            if selected_slot not in valid_slots:
                first_marker = filtered_markers[0]
                st.session_state[SELECTED_SLOT_KEY] = (
                    first_marker.day_index,
                    first_marker.event_index,
                )

        paths = _collect_paths(itinerary)
        filtered_paths = [p for p in paths if day_index is None or p.get("day_index") == day_index]

        deck = _build_deck(filtered_markers, filtered_paths)

        state = st.pydeck_chart(
            deck,
            selection_mode="single-object",
            on_select="rerun",
            key="itinerary_map",
        )

        _update_selection_from_map(state)

        selected_slot = st.session_state.get(SELECTED_SLOT_KEY)
        if selected_slot:
            day_idx, event_idx = selected_slot
            selected_marker = next(
                (marker for marker in filtered_markers if marker.day_index == day_idx and marker.event_index == event_idx),
                None,
            )
            if selected_marker:
                st.caption(f"Selected: {selected_marker.title} · {selected_marker.subtitle}")


__all__ = ["render_map_tab"]

