from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from small_state_control.core.operator import Operator
from small_state_control.core.types import (
    Action,
    DictState,
    Signal,
    StateSizeError,
    Trace,
)

if TYPE_CHECKING:
    from small_state_control.core.trace_store import TraceStore


class Controller:
    def __init__(
        self,
        operator: Operator,
        initial_state: DictState,
        controller_id: str = "default",
        state_cap_bytes: int = 4096,
        trace_store: TraceStore | None = None,
    ) -> None:
        self._operator = operator
        self._state = initial_state
        self._controller_id = controller_id
        self._state_cap_bytes = state_cap_bytes
        self._trace_store = trace_store
        self._t = 0
        self._check_state_cap(self._state)

    @property
    def controller_id(self) -> str:
        return self._controller_id

    @property
    def state(self) -> DictState:
        return self._state

    @property
    def operator(self) -> Operator:
        return self._operator

    def _check_state_cap(self, state: DictState) -> None:
        size = state.size_bytes()
        if size > self._state_cap_bytes:
            raise StateSizeError(
                f"State size {size} bytes exceeds cap of {self._state_cap_bytes} bytes"
            )

    def step(self, signal: Signal) -> tuple[Action, Trace]:
        self._check_state_cap(self._state)
        state_before = copy.deepcopy(self._state)
        new_state, action = self._operator.apply(
            copy.deepcopy(self._state), signal
        )
        self._check_state_cap(new_state)
        trace = Trace(
            t=self._t,
            controller_id=self._controller_id,
            operator_id=self._operator.operator_id,
            signal=signal,
            state_before=state_before,
            state_after=new_state,
            action=action,
        )
        self._state = new_state
        self._t += 1
        if self._trace_store is not None:
            self._trace_store.append(trace)
        return action, trace

    def replace_operator(self, operator: Operator) -> None:
        self._operator = operator

    def reset_state(self, state: DictState) -> None:
        self._check_state_cap(state)
        self._state = state

    def traces(self, last_n: int | None = None) -> list[Trace]:
        if self._trace_store is None:
            return []
        return self._trace_store.get(last_n)
