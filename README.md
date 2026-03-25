# small-state-control

A tiny Python-first kernel for compact adaptive control.

`small-state-control` is built around one simple loop:

**signal → state → operator → controller → action → trace**

The goal is to replace a class of heavy, fixed, or opaque control logic with small adaptive mechanisms that are:

- bounded
- cheap to run
- easy to inspect
- easy to trace

## Install

```bash
pip install -e .
```

Zero external dependencies.  Requires Python ≥ 3.10.

## Quick start

```python
from small_state_control import Controller, DictState, Signal
from small_state_control.operators import AIMDBudgetOperator

op = AIMDBudgetOperator(additive_inc=0.05, multiplicative_dec=0.5)
ctrl = Controller(op, DictState({"budget": 0.1}), "demo")

action, trace = ctrl.step(Signal(t=0.0, channel="pressure", value=0.3))
print(action.tag, action.payload)  # increase {'budget': 0.15, ...}
```

## What it is

A minimal runtime for systems that need to:

- observe a proxy signal
- maintain compact state
- apply a pure operator
- emit a small action
- record a structured trace

## What it is not

This is **not**:

- a generic agent framework
- an orchestration platform
- a web dashboard
- a plugin ecosystem
- a full application stack

The core should stay tiny.

## Core kernel

263 lines.  Zero dependencies.

- `Signal` — timestamped, channeled observation
- `DictState` — bounded, serializable state container
- `Action` — tagged output with payload
- `Trace` — immutable record of one step (signal, state-before, state-after, action)
- `Operator` — Protocol: `apply(state, signal) → (state, action)`
- `Controller` — step loop with state-cap enforcement and trace logging
- `TraceStore` — Protocol for trace persistence (ships with `MemoryTraceStore` and `FileTraceStore`)

## Proven operators

Three operator families from three different domains run on the same kernel:

| Operator | Domain | State | Action |
|----------|--------|-------|--------|
| `DIFEOperator` | Replay scheduling / continual learning | budget + t_last (46 bytes) | replay fraction |
| `AIMDBudgetOperator` | Resource budgeting / rate control | budget (22 bytes) | increase / decrease |
| `PIDOperator` | Classical continuous process control | integral + prev_error + t_last (~50 bytes) | PID output with P/I/D components |

Plus `SequenceOperator` for composing operators in sequence over shared state.

## Composition

```python
from small_state_control.operators import DIFEOperator, AIMDBudgetOperator, SequenceOperator

seq = SequenceOperator([DIFEOperator(), AIMDBudgetOperator()], seq_id="dife+aimd")
ctrl = Controller(seq, DictState({"budget": 0.0, "t_last": 0.0}), "composed")

action, trace = ctrl.step(Signal(t=0.0, channel="loss", value=0.7))
# action.tag == "sequence"
# action.payload["steps"] contains both sub-actions
```

`SequenceOperator` satisfies the `Operator` protocol itself, so it plugs into `Controller` with no special handling.

## Design rules

- **Small state** — bounded and serializable, enforced at every step (default 4096 bytes)
- **Pure operators** — cheap, explicit, side-effect free
- **Caller-driven runtime** — no hidden loops, no async, no event bus
- **Trace everything** — every step produces a full immutable record
- **No bloat** — if it does not help `step()`, it does not belong in core

## Measurements

| Metric | Value |
|--------|-------|
| Core kernel | 263 lines |
| Per-step latency | ~430 µs |
| State sizes | 14–64 bytes |
| Dependencies | 0 |
| Tests | 63, all passing |

### Live-system control (real signals)

PID and AIMD operators ran against real `time.perf_counter()` and
`resource.getrusage()` measurements from actual computation on a live
machine.  The PID targeted 1ms/step and visibly hunted around the
target after forced perturbations — overshoot, crash, and multi-step
recovery all captured in JSONL traces.

See `BENCHMARK_NOTE.md` for full numbers and trace analysis.

## Examples

```bash
# Synthetic replay scheduling (200 steps, JSONL traces)
python examples/replay_scheduling/run_dife_real.py

# Composed DIFE+AIMD (100 steps, JSONL traces)
python examples/composition/run_composed_control.py

# Live system metrics — PID + AIMD against real CPU/memory (80 steps)
python examples/live_metrics/run_live_control.py
```

## Intended direction

The kernel is proven with three operator families, composition, and
live-signal control.  Next:

- **Production deployment** — embed in a real system (water system telemetry, training pipeline, resource manager)
- **Ghost Meadow** — compact mergeable probabilistic state operators
- **GCA** — symbolic operator discovery feeding into the kernel at runtime
- **MicroPython port** — prove the kernel runs on ESP32

## Writing a custom operator

Any class that implements the `Operator` protocol works:

```python
from small_state_control.core.types import Action, DictState, Signal

class MyOperator:
    operator_id = "my-op"
    version = "1"

    def apply(self, state: DictState, signal: Signal) -> tuple[DictState, Action]:
        # your logic here
        return DictState({...}), Action(tag="my-action", payload={...})

    def serialize(self) -> dict:
        return {"operator_id": self.operator_id, "version": self.version}

    @classmethod
    def deserialize(cls, payload: dict) -> "MyOperator":
        return cls()
```

No base class to extend.  No registration.  No decorators.

## Writing a custom trace store

Any class that implements `append`, `get`, and `__len__` works:

```python
class RedisTraceStore:
    def append(self, trace): ...
    def get(self, last_n=None): ...
    def __len__(self): ...
```

No subclassing.  No core modification.
