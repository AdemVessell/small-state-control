from __future__ import annotations

from typing import Protocol

from small_state_control.core.types import Action, DictState, Signal


class Operator(Protocol):
    @property
    def operator_id(self) -> str: ...

    def apply(self, signal: Signal, state: DictState) -> tuple[DictState, Action]: ...
