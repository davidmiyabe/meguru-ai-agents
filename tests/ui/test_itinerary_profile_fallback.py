"""Tests for itinerary tab behaviour when the profile module cannot load."""

from __future__ import annotations

import builtins
import sys
from contextlib import nullcontext
from typing import Any, List

import pytest

from meguru.schemas import Itinerary


class _FakeColumn:
    """Minimal stand-in for a Streamlit column."""

    def __init__(self, streamlit: "_FakeStreamlit", index: int) -> None:
        self._streamlit = streamlit
        self._index = index

    def button(self, *args: Any, **kwargs: Any) -> bool:  # noqa: ARG002 - interface parity
        self._streamlit.column_calls.append(("button", self._index, args, kwargs))
        return False

    def download_button(self, *args: Any, **kwargs: Any) -> None:  # noqa: ARG002 - parity
        self._streamlit.column_calls.append(("download", self._index, args, kwargs))

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:  # noqa: ARG002
        self._streamlit.info_messages.append(message)

    def markdown(self, *args: Any, **kwargs: Any) -> None:  # noqa: ARG002
        self._streamlit.column_calls.append(("markdown", self._index, args, kwargs))

    def caption(self, *args: Any, **kwargs: Any) -> None:  # noqa: ARG002
        self._streamlit.column_calls.append(("caption", self._index, args, kwargs))

    def __enter__(self) -> "_FakeColumn":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None


class _FakeStreamlit:
    """Test double for the parts of Streamlit exercised in the fallback."""

    def __init__(self) -> None:
        self.session_state: dict[str, Any] = {}
        self.info_messages: List[str] = []
        self.column_calls: List[Any] = []

    # Basic UI helpers -------------------------------------------------
    def subheader(self, *args: Any, **kwargs: Any) -> None:  # noqa: ARG002
        return None

    def error(self, *args: Any, **kwargs: Any) -> None:  # noqa: ARG002
        return None

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:  # noqa: ARG002
        self.info_messages.append(message)

    def success(self, *args: Any, **kwargs: Any) -> None:  # noqa: ARG002
        return None

    def caption(self, *args: Any, **kwargs: Any) -> None:  # noqa: ARG002
        return None

    def write(self, *args: Any, **kwargs: Any) -> None:  # noqa: ARG002
        return None

    def markdown(self, *args: Any, **kwargs: Any) -> None:  # noqa: ARG002
        return None

    # Layout primitives ------------------------------------------------
    def columns(self, count: int, *args: Any, **kwargs: Any) -> List[_FakeColumn]:  # noqa: ARG002
        return [_FakeColumn(self, idx) for idx in range(count)]

    def radio(
        self,
        _label: str,
        *,
        options: tuple[str, ...],
        key: str,
        **_: Any,
    ) -> str:
        return self.session_state.get(key, options[0] if options else "")

    def expander(self, *args: Any, **kwargs: Any):  # noqa: ARG002
        return nullcontext()

    def container(self, *args: Any, **kwargs: Any):  # noqa: ARG002
        return nullcontext()

    def modal(self, *args: Any, **kwargs: Any):  # noqa: ARG002
        return nullcontext()

    # Form inputs ------------------------------------------------------
    def text_area(self, *args: Any, **kwargs: Any) -> str:  # noqa: ARG002
        return ""

    def text_input(self, *args: Any, **kwargs: Any) -> str:  # noqa: ARG002
        return ""

    def button(self, *args: Any, **kwargs: Any) -> bool:  # noqa: ARG002
        return False

    def download_button(self, *args: Any, **kwargs: Any) -> None:  # noqa: ARG002
        return None

    # Misc -------------------------------------------------------------
    def divider(self) -> None:
        return None

    def spinner(self, *args: Any, **kwargs: Any):  # noqa: ARG002
        return nullcontext()

    def rerun(self) -> None:
        return None


class _DummyContainer:
    def __enter__(self) -> "_DummyContainer":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None


@pytest.fixture
def restore_imports() -> None:
    """Ensure meguru.ui submodules are re-imported fresh for each test."""

    preserved = {name: sys.modules[name] for name in list(sys.modules) if name.startswith("meguru.ui")}
    for name in list(preserved):
        sys.modules.pop(name, None)
    try:
        yield
    finally:
        for name in [mod for mod in list(sys.modules) if mod.startswith("meguru.ui")]:
            sys.modules.pop(name, None)
        sys.modules.update(preserved)


def test_itinerary_tab_handles_profile_import_error(
    monkeypatch: pytest.MonkeyPatch,
    restore_imports: None,
) -> None:
    """Importing meguru.ui should still succeed when the profile tab fails."""

    del restore_imports

    original_import = builtins.__import__

    def failing_import(
        name: str,
        globals: Any | None = None,
        locals: Any | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> Any:
        if (
            name == "meguru.ui.profile"
            or (name == "meguru.ui" and fromlist and "profile" in fromlist)
            or (name == "profile" and level > 0)
        ):
            raise ImportError("synthetic profile failure")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", failing_import)

    import meguru.ui as ui

    assert ui.save_trip_to_profile is None

    itinerary_module = sys.modules["meguru.ui.itinerary"]

    fake_st = _FakeStreamlit()
    fake_st.session_state[itinerary_module._ITINERARY_KEY] = Itinerary(destination="Fallback City", days=[])
    fake_st.session_state[itinerary_module._PIPELINE_ERROR_KEY] = None
    fake_st.session_state[itinerary_module._TRIP_INTENT_KEY] = None

    monkeypatch.setattr(itinerary_module, "st", fake_st)

    ui.render_itinerary_tab(_DummyContainer())

    fallback_message = itinerary_module._PROFILE_FALLBACK_MESSAGE
    assert fallback_message is not None
    assert fallback_message in fake_st.info_messages
