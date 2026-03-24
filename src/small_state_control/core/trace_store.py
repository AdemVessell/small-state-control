from __future__ import annotations

import json
from pathlib import Path

from small_state_control.core.types import Trace


class MemoryTraceStore:
    def __init__(self) -> None:
        self._traces: list[Trace] = []

    def append(self, trace: Trace) -> None:
        self._traces.append(trace)

    @property
    def traces(self) -> list[Trace]:
        return list(self._traces)

    def __len__(self) -> int:
        return len(self._traces)


class FileTraceStore:
    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

    def append(self, trace: Trace) -> None:
        with self._path.open("a") as f:
            f.write(json.dumps(trace.to_dict()) + "\n")

    def read_all(self) -> list[dict]:
        if not self._path.exists():
            return []
        with self._path.open() as f:
            return [json.loads(line) for line in f if line.strip()]
