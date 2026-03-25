from __future__ import annotations

from typing import Any, Protocol

from small_state_control.core.types import Action, DictState, Signal


class Operator(Protocol):
    @property
    def operator_id(self) -> str: ...

    @property
    def version(self) -> str: ...

    def apply(self, state: DictState, signal: Signal) -> tuple[DictState, Action]: ...

    def serialize(self) -> dict[str, Any]: ...

    @classmethod
    def deserialize(cls, payload: dict[str, Any]) -> Operator: ...
