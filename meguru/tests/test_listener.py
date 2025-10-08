from meguru.agents.listener import _infer_travel_pace


def test_infer_travel_pace_recognises_laid_back_phrases() -> None:
    assert _infer_travel_pace("Let's keep it laid back and easy") == "Laid back"
    assert _infer_travel_pace("We're thinking a laid-back escape") == "Laid back"
