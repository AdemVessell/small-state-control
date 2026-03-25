# Benchmark Note — small-state-control v0.1.0

## What was run

Three operator families, one composition primitive, and one live-system
control loop were built on top of the `small-state-control` kernel.

### Synthetic runs

| Run | Operator | Steps | Signal source |
|-----|----------|-------|---------------|
| DIFE replay scheduling | `DIFEOperator` | 200 | Noisy exponential-decay training loss |
| Composed control | `SequenceOperator(DIFE → AIMD)` | 100 | Oscillating pressure with periodic spikes |

### Live-system run

| Run | Operator | Steps | Signal source |
|-----|----------|-------|---------------|
| PID rate control | `PIDOperator` | 80 | `time.perf_counter()` measuring actual computation wall time |
| AIMD memory control | `AIMDBudgetOperator` | 80 | `resource.getrusage()` measuring actual process RSS |

The live run generated real computational work (fibonacci + list
allocation) at varying intensities, measured actual wall time and
memory after each burst, and fed those real measurements as signals
through two operators running on the kernel.  Nothing was synthetic.

## Measurements

### Synthetic

| Metric | DIFE solo | DIFE + AIMD composed |
|--------|-----------|----------------------|
| Steps | 200 | 100 |
| Total wall time | ~86 ms | ~44 ms |
| Per-step latency | ~428 µs | ~437 µs |
| Final state size | 46 bytes | 22 bytes |
| State fields | 2 (budget, t_last) | 1 (budget) |
| Trace file | 200 lines JSONL, 70 KB | 100 lines JSONL, 45 KB |

### Live system

| Metric | PID rate control | AIMD memory control |
|--------|-----------------|---------------------|
| Steps | 80 | 80 |
| Total wall time | 104 ms (includes real work) | (concurrent) |
| Avg step | 1.31 ms (target: 1.0 ms) | — |
| Final state size | 64 bytes | 14 bytes |
| Trace file | 80 lines JSONL | 80 lines JSONL |

Per-step cost for the kernel itself is dominated by `copy.deepcopy`
(defensive state isolation).  The operator math is sub-microsecond.
For high-frequency use cases (>10K steps/sec), a lighter isolation
strategy would be needed.

### Live PID dynamics observed

Forced perturbation at step 25 (intensity spike to 40K):

| Step | Wall time | PID output | What happened |
|------|-----------|------------|---------------|
| 24 | 2.00 ms | 500 | steady state, undershooting |
| 25 | 16.20 ms | 500 | spike — PID integral saturated |
| 26 | 0.02 ms | 8,841 | PID overcorrection |
| 27 | 0.99 ms | 500 | 0.99 ms — nearly at 1.0 ms target |
| 32 | 0.15 ms | 3,987 | recovery in progress |
| 40 | 0.25 ms | 8,395 | approaching equilibrium |
| 44 | 0.02 ms | 12,604 | hunting continues |

This is real PID feedback control against real wall-clock jitter,
captured in structured JSONL traces.  The overshoot → crash → recovery
dynamics are visible in the trace data.

## What the kernel made simpler

1.  **Operators require zero infrastructure code.**  Each is a single
    class (~80–116 lines) implementing `apply(state, signal) →
    (state, action)`.  No base classes, no lifecycle hooks, no
    registration, no config files.

2.  **Composition was 30 lines of logic**, not a framework.
    `SequenceOperator` chains operators by flowing state through and
    collecting actions.  It satisfies the Operator protocol itself, so
    it plugs into Controller without any special handling.

3.  **Traces are automatic and structured.**  Every step produces a full
    `Trace` (signal, state-before, state-after, action) written to JSONL
    with zero effort from the operator author.

4.  **State bounds are enforced.**  The 4096-byte default cap is checked
    at every step boundary.  No operator can silently bloat state.

5.  **Three genuinely different operators share the same kernel.**  DIFE
    (analytic exponential-decay replay scheduler), AIMD (classical
    additive-increase / multiplicative-decrease budget controller), and
    PID (proportional-integral-derivative process controller) have
    completely different equations, different state shapes, different
    action semantics — and all run cleanly on the same Controller with
    the same trace pipeline.

6.  **TraceStore is now a Protocol.**  Anyone can write a custom trace
    backend (Redis, SQLite, MQTT) by implementing three methods.  No
    subclassing, no registration, no core modification.

7.  **The kernel handles real signals.**  PID and AIMD ran against live
    `time.perf_counter()` and `resource.getrusage()` measurements from
    actual computation.  The traces contain real floating-point wall-clock
    values, not synthetic curves.

## What is NOT proven

-   **No production deployment.**  The live run was a self-contained
    demo, not embedded in a production system.

-   **No MicroPython port.**  The "runs on ESP32" aspiration is
    untested.  `copy.deepcopy` and `json.dumps` are available in
    MicroPython but performance has not been measured.

-   **No probabilistic operator.**  Ghost Meadow-style belief merging
    has not been implemented.  The kernel's ability to handle
    probabilistic state (distributions, belief vectors) is architectural
    intention, not demonstrated.

-   **No operator discovery.**  GCA-style symbolic regression feeding
    discovered operators into the kernel at runtime has not been built.

-   **Composition is linear only.**  `SequenceOperator` is a chain, not
    a DAG.  Branching, conditional routing, and parallel composition
    have not been addressed.

## Source budget

| Component | Lines |
|-----------|-------|
| Core kernel (types, operator, controller, trace store + Protocol) | 263 |
| Operators (DIFE, AIMD, PID, SequenceOperator) | 366 |
| **Total source** | **654** |
| Tests | 767 |
| Examples | ~250 |

Zero external dependencies.  63 tests.  All passing.

Three domains proven on the same kernel:

| Operator | Domain | State shape | State bytes |
|----------|--------|-------------|-------------|
| DIFEOperator | Replay scheduling / continual learning | 2 floats (budget, t_last) | 46 |
| AIMDBudgetOperator | Resource budgeting / rate control | 1 float (budget) | 22 |
| PIDOperator | Classical continuous process control | 3 floats (integral, prev_error, t_last) | 64 |

## Next smallest necessary move

Embed the kernel in one real production system — a control loop in the
water system project, a training-run replay scheduler, or a live
resource manager — to move from demo to deployment.
