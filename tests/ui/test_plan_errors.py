"""Tests for surfacing plan tab pipeline failures."""

from __future__ import annotations

import pytest

from meguru.ui import plan


@pytest.mark.parametrize(
    "exception, expected",
    [
        (
            RuntimeError("GOOGLE_MAPS_API_KEY environment variable is not set"),
            "Unable to generate the itinerary. Add a Google Maps API key by setting the GOOGLE_MAPS_API_KEY environment variable.",
        ),
        (
            RuntimeError(
                "401 Client Error: Unauthorized for url 'https://api.openai.com/v1/chat/completions'"
            ),
            "Unable to generate the itinerary. Provide an OpenAI API key via the OPENAI_API_KEY environment variable.",
        ),
        (
            ValueError("LLM quota exceeded"),
            "Unable to generate the itinerary. LLM quota exceeded",
        ),
        (
            Exception(""),
            "Unable to generate the itinerary. Check your configuration and try again.",
        ),
    ],
)
def test_format_pipeline_error(exception: Exception, expected: str) -> None:
    assert plan._format_pipeline_error(exception) == expected


def test_format_pipeline_error_handles_non_str_messages() -> None:
    class CustomError(Exception):
        def __str__(self) -> str:
            return "Unexpected failure"

    error = CustomError()
    assert (
        plan._format_pipeline_error(error)
        == "Unable to generate the itinerary. Unexpected failure"
    )
