from __future__ import annotations

import copy

from small_state_control.core.operator import Operator
from small_state_control.core.types import Action, DictState, Signal, Trace


class Controller:
    def __init__(
        self,
        controller_id: str,
        state: DictState,
        operator: Operator,
    ) -> None:
        self._controller_id = controller_id
        self._state = state
        self._operator = operator
        self._t = 0

    @property
    def controller_id(self) -> str:
        return self._controller_id

    @property
    def state(self) -> DictState:
        return self._state

    @property
    def operator(self) -> Operator:
        return self._operator

    @operator.setter
    def operator(self, op: Operator) -> None:
        self._operator = op

    def step(self, signal: Signal) -> tuple[Action, Trace]:
        state_before = copy.deepcopy(self._state)
        new_state, action = self._operator.apply(signal, copy.deepcopy(self._state))
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
        return action, trace
