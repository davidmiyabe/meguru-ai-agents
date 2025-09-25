"""Unit tests for schema helpers and validators."""

from meguru.schemas import ResearchItem


def test_research_item_copies_place_id_into_nested_place() -> None:
    """LLM responses may omit the place id from the nested place structure."""

    item = ResearchItem.model_validate(
        {
            "place_id": "places/123",
            "place": {
                "name": "Freehand Los Angeles",
                "formatted_address": "416 W 8th St, Los Angeles, CA 90014, USA",
            },
        }
    )

    assert item.place is not None
    assert item.place.place_id == "places/123"
