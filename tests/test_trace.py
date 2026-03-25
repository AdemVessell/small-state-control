import tempfile
import unittest
from pathlib import Path

from small_state_control import (
    Action,
    DictState,
    FileTraceStore,
    MemoryTraceStore,
    Signal,
    Trace,
)


def _make_trace(**overrides):
    defaults = dict(
        t=0,
        controller_id="c",
        operator_id="op",
        signal=Signal(t=0.0, channel="test", value=None),
        state_before=DictState(),
        state_after=DictState(),
        action=Action(tag="noop"),
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

    def test_get_returns_defensive_copy(self):
        store = MemoryTraceStore()
        store.append(_make_trace())
        traces = store.get()
        traces.append(None)
        self.assertEqual(len(store), 1)

    def test_get_last_n(self):
        store = MemoryTraceStore()
        for i in range(5):
            store.append(_make_trace(t=i))
        self.assertEqual(len(store.get(last_n=3)), 3)
        self.assertEqual(store.get(last_n=3)[0].t, 2)

    def test_get_last_n_exceeding_length(self):
        store = MemoryTraceStore()
        store.append(_make_trace())
        self.assertEqual(len(store.get(last_n=10)), 1)


class TestFileTraceStore(unittest.TestCase):
    def test_write_and_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "traces.jsonl"
            store = FileTraceStore(path)

            trace = _make_trace(
                signal=Signal(t=1.0, channel="ch", value="v"),
                state_after=DictState({"a": 1}),
                action=Action(tag="do", payload={"it": True}, meta={"tag": "test"}),
            )
            store.append(trace)
            store.append(trace)

            loaded = store.get()
            self.assertEqual(len(loaded), 2)
            self.assertIsInstance(loaded[0], Trace)
            self.assertEqual(loaded[0].signal.channel, "ch")
            self.assertEqual(loaded[0].action.tag, "do")
            self.assertEqual(loaded[0].action.meta, {"tag": "test"})

    def test_get_last_n(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "traces.jsonl"
            store = FileTraceStore(path)
            for i in range(5):
                store.append(_make_trace(t=i))
            last2 = store.get(last_n=2)
            self.assertEqual(len(last2), 2)
            self.assertEqual(last2[0].t, 3)
            self.assertEqual(last2[1].t, 4)

    def test_read_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nonexistent.jsonl"
            store = FileTraceStore(path)
            self.assertEqual(store.get(), [])

    def test_len(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "traces.jsonl"
            store = FileTraceStore(path)
            self.assertEqual(len(store), 0)
            store.append(_make_trace())
            store.append(_make_trace(t=1))
            self.assertEqual(len(store), 2)

    def test_writes_valid_jsonl(self):
        import json

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "traces.jsonl"
            store = FileTraceStore(path)
            store.append(_make_trace(t=0))
            store.append(_make_trace(t=1))

            with open(path) as f:
                lines = [line for line in f if line.strip()]
            self.assertEqual(len(lines), 2)
            for line in lines:
                d = json.loads(line)
                self.assertIn("t", d)
                self.assertIn("controller_id", d)
                self.assertIn("signal", d)


class TestTrace(unittest.TestCase):
    def test_to_dict_roundtrip(self):
        trace = _make_trace(
            t=5,
            signal=Signal(t=1.5, channel="ch", value=42, meta={"k": "v"}),
            state_before=DictState({"b": 2}),
            state_after=DictState({"a": 3}),
            action=Action(tag="act", payload={"x": 4}),
        )
        d = trace.to_dict()
        trace2 = Trace.from_dict(d)
        self.assertEqual(trace, trace2)

    def test_immutable(self):
        trace = _make_trace()
        with self.assertRaises(AttributeError):
            trace.t = 99

    def test_dict_state_size_bytes(self):
        s = DictState({"a": 1})
        self.assertIsInstance(s.size_bytes(), int)
        self.assertGreater(s.size_bytes(), 0)
        empty = DictState()
        self.assertLess(empty.size_bytes(), s.size_bytes())


if __name__ == "__main__":
    unittest.main()
