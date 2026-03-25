# Benchmark Note — small-state-control v0.1.0

## What was run

Two operator families and one composition primitive were built on top of
the `small-state-control` kernel and exercised over synthetic but
realistic signal data.

| Run | Operator | Steps | Signal source |
|-----|----------|-------|---------------|
| DIFE replay scheduling | `DIFEOperator` | 200 | Noisy exponential-decay training loss |
| Composed control | `SequenceOperator(DIFE → AIMD)` | 100 | Oscillating pressure with periodic spikes |

## Measurements

| Metric | DIFE solo | DIFE + AIMD composed |
|--------|-----------|----------------------|
| Steps | 200 | 100 |
| Total wall time | ~86 ms | ~44 ms |
| Per-step latency | ~428 µs | ~437 µs |
| Final state size | 46 bytes | 22 bytes |
| State fields | 2 (budget, t_last) | 1 (budget) |
| Trace file | 200 lines JSONL, 70 KB | 100 lines JSONL, 45 KB |

Per-step cost is dominated by `copy.deepcopy` (defensive state isolation).
The operator math itself is sub-microsecond.  For high-frequency use
cases (>10K steps/sec), a lighter isolation strategy would be needed.

## What the kernel made simpler

1.  **Both operators required zero infrastructure code.**  Each is a
    single class (~80 lines) implementing `apply(state, signal) →
    (state, action)`.  No base classes to extend, no lifecycle hooks, no
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

## What is NOT proven

-   **No real external dataset.**  Signals are synthetic.  A real
    deployment (e.g., feeding actual training logs or sensor data) has
    not been demonstrated.

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
| Examples | ~100 |

Zero external dependencies.  63 tests.  All passing.

Three domains proven on the same kernel:

| Operator | Domain | State shape | State bytes |
|----------|--------|-------------|-------------|
| DIFEOperator | Replay scheduling / continual learning | 2 floats (budget, t_last) | 46 |
| AIMDBudgetOperator | Resource budgeting / rate control | 1 float (budget) | 22 |
| PIDOperator | Classical continuous process control | 3 floats (integral, prev_error, t_last) | ~50 |

## Next smallest necessary move

Deploy the kernel on one real signal source (training logs, sensor
data, or the Malaysian water system project) to move from synthetic
to production evidence.
