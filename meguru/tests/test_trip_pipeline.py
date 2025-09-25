from __future__ import annotations

import logging
from datetime import date, time
from typing import Dict, Optional

import pytest

from meguru.schemas import (
    DayPlan,
    Itinerary,
    ItineraryEvent,
    RankedItem,
    ResearchCorpus,
    ResearchItem,
    TasteProfile,
    TripIntent,
)
from meguru.workflows import trip_pipeline


SUMMARY_HTML = "<p>Kyoto adventure</p>"


def _build_research_corpus() -> ResearchCorpus:
    return ResearchCorpus(
        lodgings=[ResearchItem(place_id="stay-1")],
        dining=[ResearchItem(place_id="dine-1")],
        experiences=[
            ResearchItem(place_id="exp-1"),
            ResearchItem(place_id="exp-2"),
            ResearchItem(place_id="exp-3"),
        ],
    )


def _build_taste_profile() -> TasteProfile:
    return TasteProfile(
        top_picks=[
            RankedItem(place_id="exp-1", score=0.95),
            RankedItem(place_id="exp-2", score=0.9),
            RankedItem(place_id="dine-1", score=0.85),
        ],
        backups=[RankedItem(place_id="exp-3", score=0.6)],
    )


def _build_itinerary(destination: str) -> Itinerary:
    return Itinerary(
        destination=destination,
        start_date=date(2024, 5, 1),
        end_date=date(2024, 5, 3),
        days=[
            DayPlan(
                label="Day 1",
                summary="Cultural immersion and flavours",
                events=[
                    ItineraryEvent(
                        title="Wake up refreshed",
                        category="wake_up",
                        start_time=time(7, 0),
                        duration_minutes=30,
                        description="Light stretching and hydration at your hotel.",
                        justification="Gives you time to acclimate before breakfast.",
                    ),
                    ItineraryEvent(
                        title="Breakfast at cafe",
                        category="breakfast",
                        start_time=time(7, 30),
                        duration_minutes=60,
                        place_id="dine-1",
                        description="Savour seasonal pastries and coffee.",
                        justification="Highly rated spot that aligns with your love of food adventures.",
                    ),
                    ItineraryEvent(
                        title="Morning walk",
                        category="morning_activity",
                        start_time=time(9, 0),
                        duration_minutes=90,
                        place_id="exp-1",
                        description="Stroll the historic streets and capture photos.",
                        justification="Showcases Kyoto's culture at a relaxed pace.",
                    ),
                    ItineraryEvent(
                        title="Lunch at Nishiki Market",
                        category="lunch",
                        start_time=time(12, 30),
                        duration_minutes=75,
                        location="Nishiki Market Food Stalls",
                        description="Sample local bites and sweets.",
                        justification="An ideal way to graze through Kyoto specialities.",
                    ),
                    ItineraryEvent(
                        title="Afternoon temple",
                        category="afternoon_activity",
                        start_time=time(14, 30),
                        duration_minutes=120,
                        place_id="exp-2",
                        description="Explore Kiyomizu-dera's wooden terrace.",
                        justification="Iconic landmark that fits your cultural interests.",
                    ),
                    ItineraryEvent(
                        title="Dinner tasting menu",
                        category="dinner",
                        start_time=time(19, 0),
                        duration_minutes=90,
                        place_id="dine-1",
                        description="Multi-course kaiseki-inspired meal.",
                        justification="Celebrates Kyoto flavours in an intimate setting.",
                    ),
                ],
            ),
            DayPlan(
                label="Day 2",
                summary="Art and design inspirations",
                events=[
                    ItineraryEvent(
                        title="Wake slowly",
                        category="wake_up",
                        start_time=time(8, 0),
                        duration_minutes=30,
                        description="Gentle start with tea in your room.",
                        justification="Keeps the day relaxed after a big first day.",
                    ),
                    ItineraryEvent(
                        title="Museum visit",
                        category="morning_activity",
                        start_time=time(10, 0),
                        duration_minutes=120,
                        place_id="exp-3",
                        description="Discover modern art installations.",
                        justification="Matches your interest in design and creativity.",
                    ),
                ],
            ),
        ],
    )


def _patch_pipeline_agents(
    monkeypatch: pytest.MonkeyPatch,
    *,
    research_calls: Dict[str, int],
    prompt_versions: Optional[Dict[str, str]] = None,
    planner_destination: Optional[str] = None,
    use_real_planner: bool = False,
) -> None:
    prompt_versions = prompt_versions or {
        "intake": "intake.stub",
        "researcher": "researcher.stub",
        "taste": "taste.stub",
        "planner": "planner.stub",
        "summary": "summary.stub",
    }

    class DummyIntakeAgent:
        prompt_version = prompt_versions["intake"]

        def __init__(self, *_, **__):
            pass

        def run(self, *, free_text=None, wizard_fields=None):  # pragma: no cover - defensive
            raise AssertionError("Intake agent should not be invoked for structured intents")

    class DummyResearcherAgent:
        prompt_version = prompt_versions["researcher"]

        def run(self, trip_intent: TripIntent) -> ResearchCorpus:
            research_calls["count"] = research_calls.get("count", 0) + 1
            return _build_research_corpus()

    class DummyTasteAgent:
        prompt_version = prompt_versions["taste"]

        def run(self, trip_intent: TripIntent, corpus: ResearchCorpus) -> TasteProfile:
            return _build_taste_profile()

    class DummySummaryAgent:
        prompt_version = prompt_versions["summary"]

        def run(self, itinerary: Itinerary) -> str:
            return SUMMARY_HTML

    monkeypatch.setattr(trip_pipeline, "IntakeAgent", DummyIntakeAgent)
    monkeypatch.setattr(trip_pipeline, "ResearcherAgent", DummyResearcherAgent)
    monkeypatch.setattr(trip_pipeline, "TasteAgent", DummyTasteAgent)
    if not use_real_planner:
        class DummyPlannerAgent:
            prompt_version = prompt_versions["planner"]

            def run(
                self,
                trip_intent: TripIntent,
                taste_profile: TasteProfile,
                corpus: ResearchCorpus,
            ) -> Itinerary:
                destination = planner_destination
                if destination is None:
                    destination = trip_intent.destination
                itinerary = _build_itinerary(destination)
                if not itinerary.destination:
                    itinerary.destination = trip_intent.destination
                return itinerary

        monkeypatch.setattr(trip_pipeline, "PlannerAgent", DummyPlannerAgent)
    monkeypatch.setattr(trip_pipeline, "SummaryAgent", DummySummaryAgent)


def test_run_trip_pipeline_returns_enriched_itinerary(monkeypatch: pytest.MonkeyPatch) -> None:
    trip_pipeline.clear_research_cache()
    research_calls: Dict[str, int] = {}
    _patch_pipeline_agents(monkeypatch, research_calls=research_calls)

    intent = TripIntent(destination="Kyoto", interests=["culture", "food"])

    itinerary = trip_pipeline.run_trip_pipeline(intent)

    assert itinerary.destination == "Kyoto"
    assert itinerary.days, "Pipeline should return at least one day"
    assert len(itinerary.days[0].events) >= 3
    assert itinerary.notes == SUMMARY_HTML
    assert research_calls["count"] == 1


def test_pipeline_assigns_destination_from_intent_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trip_pipeline.clear_research_cache()
    research_calls: Dict[str, int] = {}
    _patch_pipeline_agents(
        monkeypatch,
        research_calls=research_calls,
        use_real_planner=True,
    )

    def fake_call_llm_and_validate(*_, **__) -> Itinerary:
        return Itinerary.model_validate({"days": []})

    monkeypatch.setattr(
        "meguru.agents.planner.call_llm_and_validate",
        fake_call_llm_and_validate,
    )

    intent = TripIntent(destination="Kyoto", interests=["culture"])

    itinerary = trip_pipeline.run_trip_pipeline(intent)

    assert itinerary.destination == "Kyoto"
    assert research_calls["count"] == 1


def test_research_cache_reuses_results(monkeypatch: pytest.MonkeyPatch) -> None:
    trip_pipeline.clear_research_cache()
    research_calls: Dict[str, int] = {}
    _patch_pipeline_agents(monkeypatch, research_calls=research_calls)

    intent = TripIntent(destination="Kyoto")

    trip_pipeline.run_trip_pipeline(intent)
    assert research_calls["count"] == 1

    trip_pipeline.run_trip_pipeline(intent)
    assert research_calls["count"] == 1, "Researcher should not rerun when cache hits"

    trip_pipeline.clear_research_cache()
    trip_pipeline.run_trip_pipeline(intent)
    assert research_calls["count"] == 2


def test_pipeline_logs_include_prompt_versions(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    trip_pipeline.clear_research_cache()
    research_calls: Dict[str, int] = {}
    prompt_versions = {
        "intake": "intake.test.v1",
        "researcher": "researcher.test.v2",
        "taste": "taste.test.v3",
        "planner": "planner.test.v4",
        "summary": "summary.test.v5",
    }
    _patch_pipeline_agents(
        monkeypatch,
        research_calls=research_calls,
        prompt_versions=prompt_versions,
    )

    intent = TripIntent(destination="Kyoto")

    with caplog.at_level(logging.INFO):
        trip_pipeline.run_trip_pipeline(intent)

    for stage, version in prompt_versions.items():
        assert any(
            f"[prompt_version={version}]" in record.getMessage()
            for record in caplog.records
        ), f"Expected prompt version {version} to be logged for stage {stage}"
