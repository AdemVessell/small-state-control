from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


class StateSizeError(Exception):
    """Raised when serialized state exceeds the configured cap."""


@dataclass(frozen=True, slots=True)
class Signal:
    t: float
    channel: str
    value: Any
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DictState:
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"data": self.data}

    def size_bytes(self) -> int:
        return len(json.dumps(self.data, separators=(",", ":")))


@dataclass(frozen=True, slots=True)
class Action:
    tag: str
    payload: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
            "signal": self.signal.to_dict(),
            "state_before": self.state_before.to_dict(),
            "state_after": self.state_after.to_dict(),
            "action": self.action.to_dict(),
            "meta": self.meta,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Trace:
        return Trace(
            t=d["t"],
            controller_id=d["controller_id"],
            operator_id=d["operator_id"],
            signal=Signal(**d["signal"]),
            state_before=DictState(**d["state_before"]),
            state_after=DictState(**d["state_after"]),
            action=Action(**d["action"]),
            meta=d.get("meta", {}),
        )
