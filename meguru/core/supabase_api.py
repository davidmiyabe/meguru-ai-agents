"""Minimal Supabase REST API client used by the Meguru application."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional

import requests


class SupabaseError(RuntimeError):
    """Raised when a Supabase API request fails."""


@dataclass(slots=True)
class SupabaseUser:
    """Supabase authenticated user representation."""

    id: str
    email: Optional[str]
    raw: Mapping[str, Any]


@dataclass(slots=True)
class SupabaseSession:
    """Authentication session details returned by Supabase."""

    access_token: str
    refresh_token: str
    token_type: str
    expires_at: Optional[int]
    user: SupabaseUser

    def is_expired(self, *, safety_seconds: int = 60) -> bool:
        """Return ``True`` if the token has expired or is close to expiring."""

        if not self.expires_at:
            return False
        return time.time() >= (self.expires_at - safety_seconds)


class SupabaseClient:
    """Very small wrapper around Supabase's REST and auth HTTP APIs."""

    def __init__(self, url: str, anon_key: str, *, http_session: Optional[requests.Session] = None) -> None:
        self._url = url.rstrip("/")
        self._anon_key = anon_key
        self._session = http_session or requests.Session()
        self._session.headers.setdefault("apikey", anon_key)

    @property
    def url(self) -> str:
        return self._url

    @property
    def anon_key(self) -> str:
        return self._anon_key

    @classmethod
    def from_env(cls) -> "SupabaseClient | None":
        """Return a client instance using ``SUPABASE_URL`` and ``SUPABASE_ANON_KEY``."""

        url = os.getenv("SUPABASE_URL")
        anon_key = os.getenv("SUPABASE_ANON_KEY")
        if not url or not anon_key:
            return None
        return cls(url, anon_key)

    def _auth_request(
        self,
        method: str,
        path: str,
        *,
        payload: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        endpoint = f"{self._url}/auth/v1{path}"
        response = self._session.request(
            method,
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json", "apikey": self._anon_key},
            timeout=30,
        )
        if response.status_code >= 400:
            raise SupabaseError(f"Supabase auth request failed ({response.status_code}): {response.text}")
        data: Dict[str, Any] = response.json()
        return data

    def _rest_request(
        self,
        method: str,
        path: str,
        *,
        access_token: str,
        params: Optional[Mapping[str, Any]] = None,
        payload: Optional[Any] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
    ) -> Any:
        endpoint = f"{self._url}/rest/v1/{path.lstrip('/')}"
        headers: MutableMapping[str, str] = {
            "Authorization": f"Bearer {access_token}",
            "apikey": self._anon_key,
        }
        if extra_headers:
            headers.update(extra_headers)
        if method.upper() in {"POST", "PATCH", "PUT"}:
            headers.setdefault("Content-Type", "application/json")
        response = self._session.request(
            method,
            endpoint,
            params=params,
            json=payload,
            headers=headers,
            timeout=30,
        )
        if response.status_code >= 400:
            raise SupabaseError(
                f"Supabase REST request failed ({response.status_code}) for {path}: {response.text}"
            )
        if response.text:
            try:
                return response.json()
            except ValueError:
                return response.text
        return None

    @staticmethod
    def _parse_session(payload: Mapping[str, Any]) -> SupabaseSession:
        user_data = payload.get("user") or {}
        access_token = payload.get("access_token")
        refresh_token = payload.get("refresh_token")
        token_type = payload.get("token_type", "bearer")
        expires_at = payload.get("expires_at")
        if not access_token or not refresh_token:
            raise SupabaseError("Supabase auth response missing access or refresh token")
        user_id = user_data.get("id")
        if not user_id:
            raise SupabaseError("Supabase auth response missing user id")
        user_email = user_data.get("email")
        user = SupabaseUser(id=user_id, email=user_email, raw=dict(user_data))
        return SupabaseSession(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type=token_type,
            expires_at=expires_at,
            user=user,
        )

    def sign_in_with_password(self, email: str, password: str) -> SupabaseSession:
        payload = {"email": email, "password": password}
        data = self._auth_request("POST", "/token?grant_type=password", payload=payload)
        return self._parse_session(data)

    def sign_up_with_password(self, email: str, password: str) -> SupabaseSession:
        payload = {"email": email, "password": password}
        data = self._auth_request("POST", "/signup", payload=payload)
        return self._parse_session(data)

    def refresh_session(self, refresh_token: str) -> SupabaseSession:
        payload = {"refresh_token": refresh_token}
        data = self._auth_request("POST", "/token?grant_type=refresh_token", payload=payload)
        return self._parse_session(data)

    def select(
        self,
        table: str,
        *,
        access_token: str,
        filters: Optional[Mapping[str, Any]] = None,
        select: Optional[str] = None,
        order: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        if filters:
            params.update(filters)
        if select:
            params["select"] = select
        if order:
            params["order"] = order
        if limit is not None:
            params["limit"] = limit
        result = self._rest_request("GET", table, access_token=access_token, params=params)
        if isinstance(result, list):
            return result
        return []

    def insert(
        self,
        table: str,
        rows: Iterable[Mapping[str, Any]],
        *,
        access_token: str,
        returning: bool = True,
        prefer_resolution: Optional[str] = None,
        on_conflict: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        payload = list(rows)
        if not payload:
            return []
        params: Dict[str, Any] = {}
        if on_conflict:
            params["on_conflict"] = on_conflict
        prefer_parts = []
        if returning:
            prefer_parts.append("return=representation")
        if prefer_resolution:
            prefer_parts.append(f"resolution={prefer_resolution}")
        headers: Dict[str, str] = {}
        if prefer_parts:
            headers["Prefer"] = ",".join(prefer_parts)
        result = self._rest_request(
            "POST",
            table,
            access_token=access_token,
            params=params,
            payload=payload,
            extra_headers=headers,
        )
        if isinstance(result, list):
            return result
        return []

    def update(
        self,
        table: str,
        *,
        access_token: str,
        filters: Mapping[str, Any],
        values: Mapping[str, Any],
        returning: bool = False,
    ) -> List[Dict[str, Any]]:
        prefer = "return=representation" if returning else None
        headers = {"Prefer": prefer} if prefer else None
        result = self._rest_request(
            "PATCH",
            table,
            access_token=access_token,
            params=dict(filters),
            payload=dict(values),
            extra_headers=headers,
        )
        if isinstance(result, list):
            return result
        return []


__all__ = ["SupabaseClient", "SupabaseSession", "SupabaseUser", "SupabaseError"]

