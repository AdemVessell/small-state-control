#!/usr/bin/env python3
"""Composed DIFE + AIMD control over a simulated resource-pressure signal.

Runs a SequenceOperator (DIFE → AIMD) for 100 steps with an oscillating
pressure signal, emits JSONL traces, and prints timing/state-size summary.

Usage:
    python examples/composition/run_composed_control.py
"""

import json
import math
import time
from pathlib import Path

from small_state_control import Controller, DictState, FileTraceStore, Signal
from small_state_control.operators.aimd import AIMDBudgetOperator
from small_state_control.operators.compose import SequenceOperator
from small_state_control.operators.dife import DIFEOperator


def pressure_signal(t: float) -> float:
    """Oscillating pressure: slow sine + spike every 25 steps."""
    base = 0.4 + 0.3 * math.sin(t * 0.2)
    spike = 0.4 if int(t) % 25 == 0 and t > 0 else 0.0
    return min(base + spike, 1.0)


def main() -> None:
    n_steps = 100
    trace_path = Path(__file__).parent / "composed_traces.jsonl"
    trace_path.unlink(missing_ok=True)

    store = FileTraceStore(trace_path)
    dife = DIFEOperator(lam=0.3, threshold=1.0, decay=0.9, gain=0.2, floor=0.0, ceiling=1.0)
    aimd = AIMDBudgetOperator(additive_inc=0.03, multiplicative_dec=0.5, pressure_threshold=0.6)
    seq = SequenceOperator([dife, aimd], seq_id="dife+aimd")

    ctrl = Controller(
        seq,
        DictState({"budget": 0.1, "t_last": 0.0}),
        "composed-demo",
        trace_store=store,
    )

    t0 = time.perf_counter_ns()
    for i in range(n_steps):
        p = pressure_signal(float(i))
        ctrl.step(Signal(t=float(i), channel="pressure", value=p))
    elapsed_ns = time.perf_counter_ns() - t0

    final_state = ctrl.state
    state_bytes = final_state.size_bytes()
    per_step_us = elapsed_ns / n_steps / 1000

    print(f"Steps:          {n_steps}")
    print(f"Total time:     {elapsed_ns / 1e6:.2f} ms")
    print(f"Per step:       {per_step_us:.1f} µs")
    print(f"Final state:    {json.dumps(final_state.data)}")
    print(f"State size:     {state_bytes} bytes")
    print(f"Traces written: {trace_path}")

    # trace shape check
    traces = store.get(last_n=3)
    for tr in traces:
        steps = tr.action.payload.get("steps", [])
        print(f"  t={tr.t}: {steps[0]['tag']} → {steps[1]['tag']}, budget={tr.state_after.data.get('budget')}")


if __name__ == "__main__":
    main()
