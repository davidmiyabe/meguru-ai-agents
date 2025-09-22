"""Centralised LLM client utilities."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence

import httpx


DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0"))
DEFAULT_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "60"))
_MAX_TOKENS_ENV = os.getenv("LLM_MAX_TOKENS")
DEFAULT_MAX_TOKENS: Optional[int] = int(_MAX_TOKENS_ENV) if _MAX_TOKENS_ENV else None


_LOGGER = logging.getLogger(__name__)


def _clean_dict(payload: MutableMapping[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


@dataclass
class LLMClient:
    """A small convenience wrapper for calling chat based LLM APIs."""

    model: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    timeout: Optional[float] = DEFAULT_TIMEOUT
    max_tokens: Optional[int] = DEFAULT_MAX_TOKENS
    api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    def chat(
        self,
        *,
        prompt: str,
        system: str,
        model: Optional[str] = None,
        stop: Optional[Sequence[str]] = None,
        prompt_version: str,
        temperature: Optional[float] = None,
        timeout: Optional[float] = None,
        max_tokens: Optional[int] = None,
        force_json: bool = False,
    ) -> Dict[str, Any]:
        """Call the backing LLM API and return its raw response."""

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]

        if force_json:
            messages.append(
                {
                    "role": "system",
                    "content": "You must respond with a valid JSON object and nothing else.",
                }
            )

        payload: Dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
            "stop": list(stop) if stop else None,
            "user": prompt_version,
            "response_format": {"type": "json_object"} if force_json else None,
        }

        payload = _clean_dict(payload)

        _LOGGER.debug(
            "Calling chat completion model %s [prompt_version=%s]",
            payload["model"],
            prompt_version,
        )

        request_timeout = timeout if timeout is not None else self.timeout
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        request_kwargs: Dict[str, Any] = {}
        if request_timeout is not None:
            request_kwargs["timeout"] = request_timeout

        response = httpx.post(
            f"{self.base_url.rstrip('/')}/chat/completions",
            json=payload,
            headers=headers,
            **request_kwargs,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def extract_content(response: Mapping[str, Any]) -> str:
        """Extract the assistant message content from a chat completion response."""

        choices = response.get("choices")
        if not choices:
            raise ValueError("LLM response did not contain any choices")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if content is None:
            raise ValueError("LLM response did not contain content")
        return content


_default_client = LLMClient()


def llm_json(
    prompt: str,
    system: str,
    model: str,
    stop: Optional[Sequence[str]],
    prompt_version: str,
) -> Dict[str, Any]:
    """Call the shared LLM client expecting a JSON response."""

    try:
        response = _default_client.chat(
            prompt=prompt,
            system=system,
            model=model,
            stop=stop,
            prompt_version=prompt_version,
        )
        content = _default_client.extract_content(response)
        return json.loads(content)
    except json.JSONDecodeError:
        retry_response = _default_client.chat(
            prompt=prompt,
            system=system,
            model=model,
            stop=stop,
            prompt_version=prompt_version,
            force_json=True,
        )
        retry_content = _default_client.extract_content(retry_response)
        return json.loads(retry_content)


__all__ = ["LLMClient", "llm_json"]
