#!/usr/bin/env python3
"""Live network latency → operator control.

Measures real HTTP response times to public servers and feeds actual
latency measurements through two operators:

    1. PID controller targeting a latency budget (100ms) — outputs a
       throttle score indicating how aggressively to back off
    2. AIMD budget controller — cuts request budget on latency spikes,
       grows it back during calm periods

Every signal value is a real network roundtrip measured by
time.perf_counter() through actual internet infrastructure.
Nothing is synthetic.  Results will vary on every run.

Usage:
    python examples/live_network/run_latency_control.py
"""

import time
import urllib.request
from pathlib import Path

from small_state_control import Controller, DictState, FileTraceStore, Signal
from small_state_control.operators.aimd import AIMDBudgetOperator
from small_state_control.operators.pid import PIDOperator


# Real public endpoints with varying latency characteristics
TARGETS = [
    "https://www.google.com",
    "https://api.github.com",
    "https://example.com",
    "https://httpbin.org/status/200",
    "https://www.google.com",      # repeat fast ones to create mix
    "https://api.github.com",
]


def measure_latency(url: str, timeout: float = 5.0) -> float:
    """Measure real HTTP HEAD roundtrip time in seconds."""
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(url, method="HEAD")
        resp = urllib.request.urlopen(req, timeout=timeout)
        resp.close()
    except Exception:
        return timeout  # treat failure as max latency
    return time.perf_counter() - t0


def main() -> None:
    n_steps = 40
    target_s = 0.100  # 100ms target latency
    spike_threshold_s = 0.200  # 200ms = "pressure"

    trace_dir = Path(__file__).parent
    pid_path = trace_dir / "pid_latency_traces.jsonl"
    aimd_path = trace_dir / "aimd_latency_traces.jsonl"
    pid_path.unlink(missing_ok=True)
    aimd_path.unlink(missing_ok=True)

    # warmup — first request has TLS overhead
    measure_latency(TARGETS[0])

    # --- PID: target 100ms latency, output = throttle score ----------------
    pid_store = FileTraceStore(pid_path)
    pid_op = PIDOperator(
        kp=5.0,           # 100ms error → 0.5 throttle change
        ki=1.0,           # integral eliminates offset
        kd=0.5,           # derivative damps oscillation
        setpoint=target_s,
        output_min=0.0,   # 0 = no throttle (all clear)
        output_max=1.0,   # 1 = max throttle (back off fully)
        integral_min=-1.0,
        integral_max=1.0,
    )
    pid_ctrl = Controller(
        pid_op,
        DictState({"integral": 0.0, "prev_error": 0.0, "t_last": -1.0}),
        "pid-latency",
        trace_store=pid_store,
    )

    # --- AIMD: cut budget on latency spikes --------------------------------
    aimd_store = FileTraceStore(aimd_path)
    aimd_op = AIMDBudgetOperator(
        additive_inc=0.05,
        multiplicative_dec=0.5,
        floor=0.1,
        ceiling=1.0,
        pressure_threshold=0.5,  # pressure > 0.5 = cut budget
    )
    aimd_ctrl = Controller(
        aimd_op,
        DictState({"budget": 0.8}),
        "aimd-latency",
        trace_store=aimd_store,
    )

    print(f"Live network control: {n_steps} steps")
    print(f"PID target: {target_s*1000:.0f}ms | AIMD spike threshold: {spike_threshold_s*1000:.0f}ms")
    print(f"Targets: {', '.join(set(TARGETS))}")
    print()
    hdr = f"{'#':>3s} | {'host':>22s} | {'lat_ms':>7s} | {'pressure':>8s} | {'pid_throttle':>12s} | {'aimd':>8s} | {'budget':>6s}"
    print(hdr)
    print("-" * len(hdr))

    latencies = []
    total_t0 = time.perf_counter()

    for i in range(n_steps):
        url = TARGETS[i % len(TARGETS)]
        host = url.split("//")[1].split("/")[0]

        latency = measure_latency(url)
        latencies.append(latency)

        # pressure: how far above spike threshold (0 = fine, 1 = very bad)
        pressure = max(0.0, min((latency - target_s) / (spike_threshold_s - target_s), 1.0))

        # PID: signal = actual latency
        pid_action, _ = pid_ctrl.step(
            Signal(t=float(i), channel="http_latency_s", value=latency)
        )
        throttle = pid_action.payload["output"]

        # AIMD: signal = pressure derived from latency
        aimd_action, _ = aimd_ctrl.step(
            Signal(t=float(i), channel="latency_pressure", value=pressure)
        )

        print(
            f"{i:3d} | {host:>22s} | {latency*1000:7.1f} | {pressure:8.3f} | "
            f"{throttle:12.4f} | {aimd_action.tag:>8s} | {aimd_action.payload['budget']:.3f}"
        )

    total_wall = time.perf_counter() - total_t0

    # --- Summary -----------------------------------------------------------
    import statistics
    print()
    print(f"Total wall time:  {total_wall:.1f}s")
    print(f"Latency mean:     {statistics.mean(latencies)*1000:.1f}ms")
    print(f"Latency stdev:    {statistics.stdev(latencies)*1000:.1f}ms")
    print(f"Latency min:      {min(latencies)*1000:.1f}ms")
    print(f"Latency max:      {max(latencies)*1000:.1f}ms")
    print()
    print(f"PID final state:  {pid_ctrl.state.data} ({pid_ctrl.state.size_bytes()} bytes)")
    print(f"AIMD final state: {aimd_ctrl.state.data} ({aimd_ctrl.state.size_bytes()} bytes)")
    print(f"PID traces:       {pid_path} ({len(pid_store)} lines)")
    print(f"AIMD traces:      {aimd_path} ({len(aimd_store)} lines)")

    # verify traces are real
    print()
    last_pid = pid_store.get(last_n=1)[0]
    last_aimd = aimd_store.get(last_n=1)[0]
    print(f"Last PID signal:  channel={last_pid.signal.channel} value={last_pid.signal.value:.6f}s")
    print(f"Last AIMD signal: channel={last_aimd.signal.channel} value={last_aimd.signal.value:.4f}")


if __name__ == "__main__":
    main()
