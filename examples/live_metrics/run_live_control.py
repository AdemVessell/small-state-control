#!/usr/bin/env python3
"""Live system metrics → operator control.

Generates real, varying computational work on this machine, measures
actual process-level metrics (wall time, CPU time, RSS memory) after
each burst, and feeds those real measurements through two operators:

    1. PID controller targeting 1ms per work-step by adjusting intensity
    2. AIMD budget controller responding to real memory pressure

Every signal value comes from time.perf_counter() and resource.getrusage()
measuring actual work on this machine.  Nothing is synthetic.

Usage:
    python examples/live_metrics/run_live_control.py
"""

import resource
import time
from pathlib import Path

from small_state_control import Controller, DictState, FileTraceStore, Signal
from small_state_control.operators.aimd import AIMDBudgetOperator
from small_state_control.operators.pid import PIDOperator


def do_real_work(intensity: int) -> list[int]:
    """Burn real CPU cycles and allocate real memory."""
    a, b = 0, 1
    for _ in range(int(intensity)):
        a, b = b, a + b
    return list(range(max(1, int(intensity) // 10)))


def get_rss_kb() -> int:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


def main() -> None:
    n_steps = 80
    target_ms = 1.0

    trace_dir = Path(__file__).parent
    pid_path = trace_dir / "pid_live_traces.jsonl"
    aimd_path = trace_dir / "aimd_live_traces.jsonl"
    pid_path.unlink(missing_ok=True)
    aimd_path.unlink(missing_ok=True)

    # warmup
    do_real_work(10000)

    # --- PID: adjust work intensity to hit target wall time ----------------
    #
    # On this machine, ~10K intensity ≈ 1ms.  The PID output IS intensity.
    # We use proportional-on-error: if wall_time < target, increase intensity.
    # Gains are tuned so that 1ms of error ≈ 10K intensity change.
    pid_store = FileTraceStore(pid_path)
    pid_op = PIDOperator(
        kp=10_000_000.0,    # 1ms error → 10K intensity delta
        ki=1_000_000.0,     # integral helps eliminate steady-state offset
        kd=500_000.0,       # derivative damps oscillation
        setpoint=target_ms / 1000.0,
        output_min=500,
        output_max=60000,
        integral_min=-0.01,
        integral_max=0.01,
    )
    pid_ctrl = Controller(
        pid_op,
        DictState({"integral": 0.0, "prev_error": 0.0, "t_last": -1.0}),
        "pid-rate",
        trace_store=pid_store,
    )

    # --- AIMD: respond to real memory pressure -----------------------------
    aimd_store = FileTraceStore(aimd_path)
    aimd_op = AIMDBudgetOperator(
        additive_inc=0.03,
        multiplicative_dec=0.5,
        floor=0.05,
        ceiling=1.0,
        pressure_threshold=0.4,
    )
    aimd_ctrl = Controller(
        aimd_op,
        DictState({"budget": 0.5}),
        "aimd-mem",
        trace_store=aimd_store,
    )

    rss_baseline = get_rss_kb()
    rss_ceiling = rss_baseline + 30000

    print(f"Live control: {n_steps} steps, target {target_ms}ms/step")
    print(f"RSS baseline: {rss_baseline}KB, pressure ceiling: +30MB")
    print()
    hdr = f"{'step':>4s} | {'wall_ms':>7s} | {'rss_KB':>7s} | {'pressure':>8s} | {'intens':>7s} | {'pid_out':>9s} | {'aimd':>8s} | {'budget':>6s}"
    print(hdr)
    print("-" * len(hdr))

    intensity = 8000.0
    _heap = []
    total_wall = 0.0
    walls = []

    for i in range(n_steps):
        # perturbation: force intensity spikes at step 25 and 55
        if i == 25:
            intensity = 40000.0
        elif i == 55:
            intensity = 35000.0

        t0 = time.perf_counter()
        result = do_real_work(intensity)
        wall = time.perf_counter() - t0
        total_wall += wall
        walls.append(wall)

        _heap.append(result)
        if len(_heap) > 25:
            _heap = _heap[-12:]

        rss = get_rss_kb()
        pressure = max(0.0, min((rss - rss_baseline) / max(rss_ceiling - rss_baseline, 1), 1.0))

        pid_action, _ = pid_ctrl.step(Signal(t=float(i), channel="step_wall_s", value=wall))
        intensity = max(500, min(pid_action.payload["output"], 60000))

        aimd_action, _ = aimd_ctrl.step(Signal(t=float(i), channel="mem_pressure", value=pressure))

        if i % 4 == 0 or i == n_steps - 1 or i in (25, 26, 27, 55, 56, 57):
            print(
                f"{i:4d} | {wall*1000:7.2f} | {rss:7d} | {pressure:8.3f} | "
                f"{int(intensity):7d} | {pid_action.payload['output']:+9.0f} | "
                f"{aimd_action.tag:>8s} | {aimd_action.payload['budget']:.3f}"
            )

    avg_wall = sum(walls) / len(walls) * 1000
    print()
    print(f"Total wall:       {total_wall*1000:.1f}ms")
    print(f"Avg step:         {avg_wall:.2f}ms (target: {target_ms}ms)")
    print(f"Steps near target: {sum(1 for w in walls if abs(w*1000 - target_ms) < 0.5)}/{n_steps}")
    print(f"PID final state:  {pid_ctrl.state.data} ({pid_ctrl.state.size_bytes()} bytes)")
    print(f"AIMD final state: {aimd_ctrl.state.data} ({aimd_ctrl.state.size_bytes()} bytes)")
    print(f"PID traces:       {pid_path} ({len(pid_store)} lines)")
    print(f"AIMD traces:      {aimd_path} ({len(aimd_store)} lines)")


if __name__ == "__main__":
    main()
