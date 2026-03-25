from __future__ import annotations

import json
from pathlib import Path

from small_state_control.core.types import Trace


class MemoryTraceStore:
    def __init__(self) -> None:
        self._traces: list[Trace] = []

    def append(self, trace: Trace) -> None:
        self._traces.append(trace)

    def get(self, last_n: int | None = None) -> list[Trace]:
        if last_n is None:
            return list(self._traces)
        return list(self._traces[-last_n:])

    def __len__(self) -> int:
        return len(self._traces)


class FileTraceStore:
    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

    def append(self, trace: Trace) -> None:
        with self._path.open("a") as f:
            f.write(json.dumps(trace.to_dict(), separators=(",", ":")) + "\n")

    def get(self, last_n: int | None = None) -> list[Trace]:
        if not self._path.exists():
            return []
        with self._path.open() as f:
            lines = [line for line in f if line.strip()]
        if last_n is not None:
            lines = lines[-last_n:]
        return [Trace.from_dict(json.loads(line)) for line in lines]

    def __len__(self) -> int:
        if not self._path.exists():
            return 0
        with self._path.open() as f:
            return sum(1 for line in f if line.strip())
