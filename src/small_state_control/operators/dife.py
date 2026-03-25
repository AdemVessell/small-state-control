"""DIFE — Decaying Information Forgetting Envelope.

A compact analytic operator for replay scheduling in continual-learning
or data-retention systems.  Given a signal carrying a staleness or loss
metric, DIFE maintains a small state (replay budget + last-event time)
and emits an action recommending how much old data to replay.

Core equation:
    weight = exp(-λ · Δt) · clamp(signal_value / threshold, 0, 1)
    budget  = clamp(budget_prev · decay + weight · gain, floor, ceiling)

All parameters are scalars.  State is two floats.
"""

from __future__ import annotations

import math
from typing import Any

from small_state_control.core.types import Action, DictState, Signal


class DIFEOperator:
    """Exponential-decay replay budget operator."""

    def __init__(
        self,
        lam: float = 1.0,
        threshold: float = 1.0,
        decay: float = 0.95,
        gain: float = 0.1,
        floor: float = 0.0,
        ceiling: float = 1.0,
    ) -> None:
        self._lam = lam
        self._threshold = threshold
        self._decay = decay
        self._gain = gain
        self._floor = floor
        self._ceiling = ceiling

    # ---- Operator protocol ------------------------------------------------

    @property
    def operator_id(self) -> str:
        return "dife"

    @property
    def version(self) -> str:
        return "1"

    def apply(self, state: DictState, signal: Signal) -> tuple[DictState, Action]:
        budget = state.data.get("budget", 0.0)
        t_last = state.data.get("t_last", signal.t)

        dt = max(signal.t - t_last, 0.0)
        raw = signal.value if isinstance(signal.value, (int, float)) else 0.0
        normed = max(0.0, min(raw / self._threshold, 1.0))
        weight = math.exp(-self._lam * dt) * normed

        new_budget = budget * self._decay + weight * self._gain
        new_budget = max(self._floor, min(new_budget, self._ceiling))

        new_state = DictState({"budget": new_budget, "t_last": signal.t})
        action = Action(
            tag="replay",
            payload={"fraction": round(new_budget, 6)},
        )
        return new_state, action

    def serialize(self) -> dict[str, Any]:
        return {
            "operator_id": self.operator_id,
            "version": self.version,
            "lam": self._lam,
            "threshold": self._threshold,
            "decay": self._decay,
            "gain": self._gain,
            "floor": self._floor,
            "ceiling": self._ceiling,
        }

    @classmethod
    def deserialize(cls, payload: dict[str, Any]) -> "DIFEOperator":
        return cls(
            lam=payload["lam"],
            threshold=payload["threshold"],
            decay=payload["decay"],
            gain=payload["gain"],
            floor=payload["floor"],
            ceiling=payload["ceiling"],
        )
