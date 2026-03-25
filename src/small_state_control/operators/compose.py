"""Minimal operator composition.

SequenceOperator chains two or more operators:
    signal is delivered to each operator in order.
    state flows through: output state of op[i] is input state of op[i+1].
    actions are collected into a list in the composite action payload.
    the composite action tag is "sequence".

This is the simplest useful composition primitive.  It is *not* a DAG
runner, a pipeline framework, or a plugin system.  It is 30 lines of
logic that proves two operators can share a step.
"""

from __future__ import annotations

from typing import Any

from small_state_control.core.types import Action, DictState, Signal


class SequenceOperator:
    """Run a list of operators in order over shared state."""

    def __init__(self, operators: list[Any], seq_id: str = "sequence") -> None:
        if len(operators) < 2:
            raise ValueError("SequenceOperator requires at least 2 operators")
        self._operators = list(operators)
        self._seq_id = seq_id

    @property
    def operator_id(self) -> str:
        return self._seq_id

    @property
    def version(self) -> str:
        return "1"

    def apply(self, state: DictState, signal: Signal) -> tuple[DictState, Action]:
        actions: list[dict[str, Any]] = []
        current_state = state

        for op in self._operators:
            current_state, action = op.apply(current_state, signal)
            actions.append(action.to_dict())

        composite_action = Action(
            tag="sequence",
            payload={"steps": actions},
        )
        return current_state, composite_action

    def serialize(self) -> dict[str, Any]:
        return {
            "operator_id": self.operator_id,
            "version": self.version,
            "seq_id": self._seq_id,
            "operators": [op.serialize() for op in self._operators],
        }

    @classmethod
    def deserialize(cls, payload: dict[str, Any]) -> "SequenceOperator":
        raise NotImplementedError(
            "SequenceOperator.deserialize requires an operator registry; "
            "intentionally left unimplemented to avoid framework creep."
        )
