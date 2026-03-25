# small-state-control

A tiny Python-first kernel for compact adaptive control.

`small-state-control` is built around one simple loop:

**signal → state → operator → controller → action → trace**

The goal is to replace a class of heavy, fixed, or opaque control logic with small adaptive mechanisms that are:

- bounded
- cheap to run
- easy to inspect
- easy to trace

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

## Core primitives

Current kernel concepts:

- `Signal`
- `DictState`
- `Action`
- `Trace`
- `Operator`
- `Controller`
- `MemoryTraceStore`
- `FileTraceStore`

## Design rules

- **Small state** — bounded and serializable
- **Pure operators** — cheap, explicit, side-effect free
- **Caller-driven runtime** — no hidden loops
- **Trace everything** — every step leaves an artifact
- **No bloat** — if it does not help `step()`, it probably does not belong in core

## Intended direction

This repo is the kernel first.

It is meant to support compact controller families such as:

- **DIFE** — compact analytic envelope operators
- **Memory Vortex** — live adaptive controller families
- **GCA** — symbolic compression / operator-discovery
- **Ghost Meadow** — compact mergeable probabilistic state

## Usage sketch

```python
from small_state_control import Controller, DictState, Signal

ctrl = Controller(
    operator=my_operator,
    initial_state=DictState({"budget": 0.1}),
    controller_id="demo",
)

action, trace = ctrl.step(
    Signal(t=0.0, channel="pressure", value=0.42)
)
