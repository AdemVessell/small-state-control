from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

Signal = dict[str, Any]
DictState = dict[str, Any]
Action = dict[str, Any]


@dataclass(frozen=True, slots=True)
class Trace:
    t: int
    controller_id: str
    operator_id: str
    signal: Signal
    state_before: DictState
    state_after: DictState
    action: Action
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "t": self.t,
            "controller_id": self.controller_id,
            "operator_id": self.operator_id,
            "signal": self.signal,
            "state_before": self.state_before,
            "state_after": self.state_after,
            "action": self.action,
            "meta": self.meta,
        }
