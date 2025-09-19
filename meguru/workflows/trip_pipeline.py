"""Orchestrates the end-to-end flow for generating a trip itinerary."""

from __future__ import annotations

import json
import logging
import time
from typing import Dict, Optional

from meguru.agents import (
    IntakeAgent,
    PlannerAgent,
    ResearcherAgent,
    SummaryAgent,
    TasteAgent,
)
from meguru.schemas import Itinerary, ResearchCorpus, TasteProfile, TripIntent

_LOGGER = logging.getLogger(__name__)

_RESEARCH_CACHE: Dict[str, ResearchCorpus] = {}


def _cache_key(intent: TripIntent) -> str:
    """Return a stable cache key for a :class:`TripIntent`."""

    dump = intent.model_dump(mode="json")
    return json.dumps(dump, sort_keys=True)


def _log_stage(stage: str, duration: float, prompt_version: str, *, cached: bool = False) -> None:
    suffix = " (cache hit)" if cached else ""
    _LOGGER.info(
        "%s stage completed%s in %.2fs [prompt_version=%s]",
        stage.capitalize(),
        suffix,
        duration,
        prompt_version,
    )


def _log_stage_skipped(stage: str, reason: str, prompt_version: str) -> None:
    _LOGGER.info(
        "%s stage skipped: %s [prompt_version=%s]",
        stage.capitalize(),
        reason,
        prompt_version,
    )


def clear_research_cache() -> None:
    """Clear the in-memory cache used for research results."""

    _RESEARCH_CACHE.clear()


def _run_intake_if_needed(intent: TripIntent) -> TripIntent:
    if intent.destination:
        _log_stage_skipped(
            "intake",
            "Trip intent already structured",
            IntakeAgent.prompt_version,
        )
        return intent

    free_text = intent.notes.strip() if intent.notes else None
    if not free_text:
        raise ValueError("Trip intent must include a destination or raw notes for intake.")

    start = time.perf_counter()
    agent = IntakeAgent()
    structured = agent.run(free_text=free_text)
    _log_stage("intake", time.perf_counter() - start, agent.prompt_version)
    return structured


def _run_research(trip_intent: TripIntent) -> ResearchCorpus:
    key = _cache_key(trip_intent)
    cached = _RESEARCH_CACHE.get(key)
    start = time.perf_counter()
    if cached is not None:
        _log_stage("researcher", time.perf_counter() - start, ResearcherAgent.prompt_version, cached=True)
        return cached.model_copy(deep=True)

    agent = ResearcherAgent()
    corpus = agent.run(trip_intent)
    _RESEARCH_CACHE[key] = corpus.model_copy(deep=True)
    _log_stage("researcher", time.perf_counter() - start, agent.prompt_version)
    return corpus


def _run_taste(trip_intent: TripIntent, corpus: ResearchCorpus) -> TasteProfile:
    start = time.perf_counter()
    agent = TasteAgent()
    taste_profile = agent.run(trip_intent, corpus)
    _log_stage("taste", time.perf_counter() - start, agent.prompt_version)
    return taste_profile


def _run_planner(
    trip_intent: TripIntent,
    taste_profile: TasteProfile,
    corpus: ResearchCorpus,
) -> Itinerary:
    start = time.perf_counter()
    agent = PlannerAgent()
    itinerary = agent.run(trip_intent, taste_profile, corpus)
    _log_stage("planner", time.perf_counter() - start, agent.prompt_version)
    return itinerary


def _run_summary(itinerary: Itinerary) -> Optional[str]:
    start = time.perf_counter()
    agent = SummaryAgent()
    summary_html = agent.run(itinerary)
    _log_stage("summary", time.perf_counter() - start, agent.prompt_version)
    return summary_html


def run_trip_pipeline(intent: TripIntent) -> Itinerary:
    """Execute the orchestrated pipeline for producing an itinerary."""

    pipeline_start = time.perf_counter()
    _LOGGER.info("Starting trip pipeline for destination: %s", intent.destination or "unknown")

    structured_intent = _run_intake_if_needed(intent)
    research_corpus = _run_research(structured_intent)
    taste_profile = _run_taste(structured_intent, research_corpus)
    itinerary = _run_planner(structured_intent, taste_profile, research_corpus)
    summary_html = _run_summary(itinerary)

    if summary_html and not itinerary.notes:
        itinerary.notes = summary_html

    _LOGGER.info("Trip pipeline completed in %.2fs", time.perf_counter() - pipeline_start)
    return itinerary


__all__ = ["run_trip_pipeline", "clear_research_cache"]
