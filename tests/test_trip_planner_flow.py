import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import workflows.trip_planner_flow as trip_flow


def test_run_trip_pipeline_passes_preferences_to_vision(monkeypatch):
    destination = "Kyoto"
    dates = "Nov 5-9"
    preferences = "Peaceful, tea, nature"

    def fake_researcher(dest, travel_dates, vibe):
        assert (dest, travel_dates, vibe) == (destination, dates, preferences)
        return "raw"

    def fake_taste(raw_data, vibe):
        assert (raw_data, vibe) == ("raw", preferences)
        return "filtered"

    def fake_planner(filtered, travel_dates, vibe):
        assert (filtered, travel_dates, vibe) == ("filtered", dates, preferences)
        return "calendar"

    def fake_vision(dest, vibe=None):
        assert vibe == preferences
        assert dest == destination
        return "scenic"

    def fake_summary(calendar, photo_spots):
        assert (calendar, photo_spots) == ("calendar", "scenic")
        return "summary"

    monkeypatch.setattr(trip_flow, "researcher_task", fake_researcher)
    monkeypatch.setattr(trip_flow, "taste_task", fake_taste)
    monkeypatch.setattr(trip_flow, "planner_task", fake_planner)
    monkeypatch.setattr(trip_flow, "vision_task", fake_vision)
    monkeypatch.setattr(trip_flow, "summary_task", fake_summary)

    result = trip_flow.run_trip_pipeline(destination, dates, preferences)

    assert result == "summary"
