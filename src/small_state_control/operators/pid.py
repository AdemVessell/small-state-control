"""PID — Proportional-Integral-Derivative controller.

A classical feedback controller for continuous process control.  Given a
signal carrying a measured process value and a state holding the setpoint
and error history, PID computes a corrective action.

State is four scalars: setpoint, error integral, previous error, and
last timestamp.  This is textbook PID with anti-windup (integral
clamping) and derivative-on-measurement.

This operator proves the kernel handles classical continuous control
alongside discrete scheduling (DIFE) and resource budgeting (AIMD).
"""

from __future__ import annotations

from typing import Any

from small_state_control.core.types import Action, DictState, Signal


class PIDOperator:
    """Discrete-time PID with integral anti-windup."""

    def __init__(
        self,
        kp: float = 1.0,
        ki: float = 0.0,
        kd: float = 0.0,
        setpoint: float = 0.0,
        output_min: float = -1.0,
        output_max: float = 1.0,
        integral_min: float = -10.0,
        integral_max: float = 10.0,
    ) -> None:
        self._kp = kp
        self._ki = ki
        self._kd = kd
        self._setpoint = setpoint
        self._output_min = output_min
        self._output_max = output_max
        self._integral_min = integral_min
        self._integral_max = integral_max

    # ---- Operator protocol ------------------------------------------------

    @property
    def operator_id(self) -> str:
        return "pid"

    @property
    def version(self) -> str:
        return "1"

    def apply(self, state: DictState, signal: Signal) -> tuple[DictState, Action]:
        pv = signal.value if isinstance(signal.value, (int, float)) else 0.0
        integral = state.data.get("integral", 0.0)
        prev_error = state.data.get("prev_error", 0.0)
        t_last = state.data.get("t_last", signal.t)

        dt = max(signal.t - t_last, 1e-9)  # avoid div-by-zero
        error = self._setpoint - pv

        # integral with anti-windup clamp
        integral = integral + error * dt
        integral = max(self._integral_min, min(integral, self._integral_max))

        # derivative on error
        derivative = (error - prev_error) / dt

        output = self._kp * error + self._ki * integral + self._kd * derivative
        output = max(self._output_min, min(output, self._output_max))

        new_state = DictState({
            "integral": round(integral, 9),
            "prev_error": round(error, 9),
            "t_last": signal.t,
        })
        action = Action(
            tag="pid_output",
            payload={
                "output": round(output, 9),
                "error": round(error, 9),
                "p": round(self._kp * error, 9),
                "i": round(self._ki * integral, 9),
                "d": round(self._kd * derivative, 9),
            },
        )
        return new_state, action

    def serialize(self) -> dict[str, Any]:
        return {
            "operator_id": self.operator_id,
            "version": self.version,
            "kp": self._kp,
            "ki": self._ki,
            "kd": self._kd,
            "setpoint": self._setpoint,
            "output_min": self._output_min,
            "output_max": self._output_max,
            "integral_min": self._integral_min,
            "integral_max": self._integral_max,
        }

    @classmethod
    def deserialize(cls, payload: dict[str, Any]) -> "PIDOperator":
        return cls(
            kp=payload["kp"],
            ki=payload["ki"],
            kd=payload["kd"],
            setpoint=payload["setpoint"],
            output_min=payload["output_min"],
            output_max=payload["output_max"],
            integral_min=payload["integral_min"],
            integral_max=payload["integral_max"],
        )
