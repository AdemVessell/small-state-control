import tempfile
import unittest
from pathlib import Path

from small_state_control import FileTraceStore, MemoryTraceStore, Trace


def _make_trace(**overrides):
    defaults = dict(
        t=0,
        controller_id="c",
        operator_id="op",
        signal={},
        state_before={},
        state_after={},
        action={},
    )
    defaults.update(overrides)
    return Trace(**defaults)


class TestMemoryTraceStore(unittest.TestCase):
    def test_append_and_len(self):
        store = MemoryTraceStore()
        self.assertEqual(len(store), 0)
        store.append(_make_trace())
        self.assertEqual(len(store), 1)
        store.append(_make_trace(t=1))
        self.assertEqual(len(store), 2)

    def test_traces_returns_defensive_copy(self):
        store = MemoryTraceStore()
        store.append(_make_trace())
        traces = store.traces
        traces.append(None)  # mutate returned list
        self.assertEqual(len(store), 1)  # internal list unaffected


class TestFileTraceStore(unittest.TestCase):
    def test_write_and_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "traces.jsonl"
            store = FileTraceStore(path)

            trace = _make_trace(
                signal={"k": "v"},
                state_after={"a": 1},
                action={"do": "it"},
                meta={"tag": "test"},
            )
            store.append(trace)
            store.append(trace)

            lines = store.read_all()
            self.assertEqual(len(lines), 2)
            self.assertEqual(lines[0]["signal"], {"k": "v"})
            self.assertEqual(lines[0]["meta"], {"tag": "test"})
            self.assertEqual(lines[1]["action"], {"do": "it"})

    def test_read_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nonexistent.jsonl"
            store = FileTraceStore(path)
            self.assertEqual(store.read_all(), [])


class TestTrace(unittest.TestCase):
    def test_to_dict_roundtrip(self):
        trace = _make_trace(
            t=5,
            signal={"s": 1},
            state_before={"b": 2},
            state_after={"a": 3},
            action={"act": 4},
        )
        d = trace.to_dict()
        trace2 = Trace(**d)
        self.assertEqual(trace, trace2)

    def test_immutable(self):
        trace = _make_trace()
        with self.assertRaises(AttributeError):
            trace.t = 99


if __name__ == "__main__":
    unittest.main()
