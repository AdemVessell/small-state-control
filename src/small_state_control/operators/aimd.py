"""AIMD — Additive Increase / Multiplicative Decrease budget operator.

A classical feedback controller used in TCP congestion control, resource
allocation, and rate limiting.  On a "success" signal the budget grows
linearly; on a "pressure" signal it is cut multiplicatively.

State is one float (the budget).  Deterministic.  Bounded.
"""

from __future__ import annotations

from typing import Any

from small_state_control.core.types import Action, DictState, Signal


class AIMDBudgetOperator:
    """AIMD budget controller over a single scalar resource."""

    def __init__(
        self,
        additive_inc: float = 0.01,
        multiplicative_dec: float = 0.5,
        floor: float = 0.0,
        ceiling: float = 1.0,
        pressure_threshold: float = 0.5,
    ) -> None:
        self._ai = additive_inc
        self._md = multiplicative_dec
        self._floor = floor
        self._ceiling = ceiling
        self._threshold = pressure_threshold

    # ---- Operator protocol ------------------------------------------------

    @property
    def operator_id(self) -> str:
        return "aimd"

    @property
    def version(self) -> str:
        return "1"

    def apply(self, state: DictState, signal: Signal) -> tuple[DictState, Action]:
        budget = state.data.get("budget", self._floor)
        pressure = signal.value if isinstance(signal.value, (int, float)) else 0.0

        if pressure >= self._threshold:
            new_budget = budget * self._md
            tag = "decrease"
        else:
            new_budget = budget + self._ai
            tag = "increase"

        new_budget = max(self._floor, min(new_budget, self._ceiling))
        new_state = DictState({"budget": round(new_budget, 9)})
        action = Action(
            tag=tag,
            payload={"budget": round(new_budget, 9), "pressure": pressure},
        )
        return new_state, action

    def serialize(self) -> dict[str, Any]:
        return {
            "operator_id": self.operator_id,
            "version": self.version,
            "additive_inc": self._ai,
            "multiplicative_dec": self._md,
            "floor": self._floor,
            "ceiling": self._ceiling,
            "pressure_threshold": self._threshold,
        }

    @classmethod
    def deserialize(cls, payload: dict[str, Any]) -> "AIMDBudgetOperator":
        return cls(
            additive_inc=payload["additive_inc"],
            multiplicative_dec=payload["multiplicative_dec"],
            floor=payload["floor"],
            ceiling=payload["ceiling"],
            pressure_threshold=payload["pressure_threshold"],
        )
