from __future__ import annotations

import json

from meguru.core import llm


class DummyClient:
    def __init__(self, responses: list[str]):
        self.responses = responses
        self.calls: list[dict[str, object]] = []

    def chat(self, *, prompt, system, model, stop, prompt_version, force_json=False):
        self.calls.append(
            {
                "prompt": prompt,
                "system": system,
                "model": model,
                "stop": stop,
                "prompt_version": prompt_version,
                "force_json": force_json,
            }
        )
        content = self.responses.pop(0)
        return {"choices": [{"message": {"content": content}}]}

    @staticmethod
    def extract_content(response):
        return response["choices"][0]["message"]["content"]


def test_llm_json_retries_forced_json(monkeypatch):
    dummy = DummyClient(["not json", json.dumps({"foo": "bar"})])
    monkeypatch.setattr(llm, "_default_client", dummy)

    result = llm.llm_json(
        prompt="Give me data",
        system="You are helpful",
        model="test-model",
        stop=["###"],
        prompt_version="v1",
    )

    assert result == {"foo": "bar"}
    assert len(dummy.calls) == 2
    assert dummy.calls[0]["force_json"] is False
    assert dummy.calls[1]["force_json"] is True
    assert all(call["prompt_version"] == "v1" for call in dummy.calls)
