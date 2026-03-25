# small-state-control

A tiny Python-first kernel for compact adaptive control.

`small-state-control` is an attempt to make heavy systems lighter by replacing fixed, bloated, or opaque control logic with small adaptive mechanisms built from:

**signal → state → operator → controller → action → trace**

This project is intentionally narrow.

It is **not** a generic agent framework.  
It is **not** a dashboard platform.  
It is **not** a batteries-included orchestration stack.

It is a small-state runtime for building compact controllers that can sense pressure, update bounded state, emit cheap actions, and leave interpretable traces.

---

## Why this exists

Many AI and systems problems are still controlled by:

- fixed schedules
- static thresholds
- hand-tuned heuristics
- oversized middleware
- opaque policies
- unnecessary infrastructure mass

This project explores a different path:

- **small state**
- **cheap execution**
- **adaptive behavior**
- **symbolic operators where possible**
- **traceable decisions**

The goal is not to replace all infrastructure.

The goal is to shrink the class of problems that currently require heavy control machinery.

---

## Core idea

Every control step should be expressible as:

1. observe a **signal**
2. update or carry a compact **state**
3. run an **operator**
4. let the **controller** emit an **action**
5. record a structured **trace**

That is the kernel.

---

## Current scope

This repo is currently an **early scaffold** focused on the runtime core:

- explicit core types
- a minimal operator contract
- a tiny controller loop
- bounded-state enforcement
- memory and file-backed trace stores

It is meant to become the shared substrate for compact controller families such as:

- **DIFE** — compact analytic envelope / forgetting-style operators
- **Memory Vortex** — live adaptive controller families
- **GCA** — symbolic compression / operator-discovery layer
- **Ghost Meadow** — compact mergeable probabilistic state families

Those families are part of the architecture direction, but the repo is intentionally starting with the kernel first.

---

## Design principles

### 1. Small state
State should stay bounded, serializable, and smaller than the problem it represents.

### 2. Pure operators
Operators should be cheap, explicit, and side-effect free.

### 3. Caller-driven runtime
No hidden orchestration loops.  
No framework theater.  
A caller provides signals and receives actions + traces.

### 4. Interpretable traces
Every step should leave behind a compact artifact of what happened and why.

### 5. Minimal mass
If a feature does not directly improve `step()`, it probably does not belong in core.

---

## Current core API

The package currently exposes:

- `Signal`
- `DictState`
- `Action`
- `Trace`
- `StateSizeError`
- `Operator`
- `Controller`
- `MemoryTraceStore`
- `FileTraceStore`

These are the primitive pieces of the kernel.

---

## Example mental model

A control loop in this project looks like:

- a signal arrives
- the controller passes state + signal into an operator
- the operator returns a new state and an action
- the controller enforces the state-size cap
- the step is recorded as a trace
- traces can be stored in memory or as JSONL

This is the whole philosophy:
**small adaptive control with explicit artifacts.**

---

## What belongs here

Good fits for this kernel:

- replay-budget controllers
- context-budget controllers
- verification-depth controllers
- lightweight routing logic
- symbolic control operators
- compact mergeable state primitives
- small adaptive loops with clear traces

---

## What does not belong here

Not in core:

- web dashboards
- REST APIs
- async orchestration layers
- databases
- plugin ecosystems
- full agent frameworks
- giant config systems
- hidden background services

This repo should stay tiny.

---

## Repository direction

Planned shape:

- `core/` for kernel primitives
- `operators/` for concrete operator families
- `discovery/` for offline symbolic fitting / export
- `examples/` for small end-to-end demonstrations
- `tests/` for invariants and runtime behavior

The order matters:
**kernel first, domain operators second, heavier discovery later.**

---

## Status

Early and intentionally minimal.

The current focus is to make the runtime core clean, bounded, and trustworthy before adding richer operator families.

If this project succeeds, it should make a narrow but important claim:

> a surprising amount of control logic can be compressed into small state, cheap operators, and interpretable traces.

---

## Installation

```bash
pip install -e .
