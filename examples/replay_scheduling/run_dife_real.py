#!/usr/bin/env python3
"""DIFE replay scheduling over a synthetic training-loss curve.

Generates 200 steps of noisy exponentially-decaying loss (simulating
a real training run), feeds each step through a DIFEOperator via the
kernel's Controller, writes traces to a JSONL file, and prints a
summary with timing and state-size measurements.

Usage:
    python examples/replay_scheduling/run_dife_real.py
"""

import json
import math
import random
import time
from pathlib import Path

from small_state_control import Controller, DictState, FileTraceStore, Signal
from small_state_control.operators.dife import DIFEOperator


def synthetic_loss_curve(n: int, seed: int = 42) -> list[float]:
    """Noisy exponential decay: L(t) = 0.9 * exp(-0.02t) + noise."""
    rng = random.Random(seed)
    return [
        max(0.0, 0.9 * math.exp(-0.02 * t) + rng.gauss(0, 0.05))
        for t in range(n)
    ]


def main() -> None:
    n_steps = 200
    trace_path = Path(__file__).parent / "dife_traces.jsonl"

    # Remove stale traces
    trace_path.unlink(missing_ok=True)

    store = FileTraceStore(trace_path)
    op = DIFEOperator(lam=0.5, threshold=1.0, decay=0.92, gain=0.15, floor=0.01, ceiling=0.8)
    ctrl = Controller(op, DictState({"budget": 0.0, "t_last": 0.0}), "dife-replay", trace_store=store)

    losses = synthetic_loss_curve(n_steps)

    t0 = time.perf_counter_ns()
    for i, loss in enumerate(losses):
        ctrl.step(Signal(t=float(i), channel="training_loss", value=loss))
    elapsed_ns = time.perf_counter_ns() - t0

    # ---- summary ----------------------------------------------------------
    final_state = ctrl.state
    state_bytes = final_state.size_bytes()
    per_step_us = elapsed_ns / n_steps / 1000

    print(f"Steps:          {n_steps}")
    print(f"Total time:     {elapsed_ns / 1e6:.2f} ms")
    print(f"Per step:       {per_step_us:.1f} µs")
    print(f"Final state:    {json.dumps(final_state.data)}")
    print(f"State size:     {state_bytes} bytes")
    print(f"Traces written: {trace_path}")

    # quick sanity: read back last trace
    last = store.get(last_n=1)[0]
    print(f"Last action:    {last.action.tag} → fraction={last.action.payload['fraction']}")


if __name__ == "__main__":
    main()
