import unittest

from small_state_control import (
    Action,
    Controller,
    DictState,
    MemoryTraceStore,
    Signal,
    StateSizeError,
    Trace,
)


class EchoOperator:
    """Echoes signal value into action payload, passes state through."""

    operator_id = "echo"
    version = "1"

    def apply(self, state, signal):
        return DictState(dict(state.data)), Action(tag="echo", payload={"value": signal.value})

    def serialize(self):
        return {"operator_id": self.operator_id, "version": self.version}

    @classmethod
    def deserialize(cls, payload):
        return cls()


class DoubleOperator:
    """Doubles numeric signal value."""

    operator_id = "double"
    version = "1"

    def apply(self, state, signal):
        return state, Action(tag="double", payload={"value": signal.value * 2})

    def serialize(self):
        return {"operator_id": self.operator_id, "version": self.version}

    @classmethod
    def deserialize(cls, payload):
        return cls()


def _sig(value=None, channel="test"):
    return Signal(t=0.0, channel=channel, value=value)


class TestControllerStep(unittest.TestCase):
    def test_step_returns_action_and_trace(self):
        store = MemoryTraceStore()
        ctrl = Controller(EchoOperator(), DictState({"x": 0}), "c1", trace_store=store)
        action, trace = ctrl.step(_sig("hello"))

        self.assertIsInstance(action, Action)
        self.assertIsInstance(trace, Trace)
        self.assertEqual(action.tag, "echo")
        self.assertEqual(action.payload, {"value": "hello"})
        self.assertEqual(trace.t, 0)
        self.assertEqual(trace.controller_id, "c1")
        self.assertEqual(trace.operator_id, "echo")
        self.assertEqual(trace.state_before, DictState({"x": 0}))
        self.assertEqual(trace.state_after, DictState({"x": 0}))
        self.assertEqual(trace.meta, {})

    def test_step_emits_exactly_one_trace_and_action(self):
        store = MemoryTraceStore()
        ctrl = Controller(EchoOperator(), DictState(), trace_store=store)
        result = ctrl.step(_sig(1))
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], Action)
        self.assertIsInstance(result[1], Trace)
        self.assertEqual(len(store), 1)

    def test_step_increments_t(self):
        ctrl = Controller(EchoOperator(), DictState())
        _, t0 = ctrl.step(_sig(1))
        _, t1 = ctrl.step(_sig(2))
        self.assertEqual(t0.t, 0)
        self.assertEqual(t1.t, 1)

    def test_state_progresses(self):
        class CountOperator:
            operator_id = "count"
            version = "1"

            def apply(self, state, signal):
                n = state.data.get("n", 0) + 1
                return DictState({"n": n}), Action(tag="count", payload={"n": n})

            def serialize(self):
                return {}

            @classmethod
            def deserialize(cls, payload):
                return cls()

        ctrl = Controller(CountOperator(), DictState({"n": 0}))
        a1, _ = ctrl.step(_sig(None))
        a2, _ = ctrl.step(_sig(None))
        self.assertEqual(a1.payload, {"n": 1})
        self.assertEqual(a2.payload, {"n": 2})
        self.assertEqual(ctrl.state, DictState({"n": 2}))

    def test_state_mutation_isolation(self):
        class MutatingOperator:
            operator_id = "mutator"
            version = "1"

            def apply(self, state, signal):
                state.data["dirty"] = True  # mutates the copy
                return DictState({"clean": True}), Action(tag="noop")

            def serialize(self):
                return {}

            @classmethod
            def deserialize(cls, payload):
                return cls()

        ctrl = Controller(MutatingOperator(), DictState({"x": 1}))
        ctrl.step(_sig(None))
        self.assertEqual(ctrl.state, DictState({"clean": True}))
        self.assertNotIn("dirty", ctrl.state.data)


class TestControllerTraceStore(unittest.TestCase):
    def test_trace_auto_appended_to_store(self):
        store = MemoryTraceStore()
        ctrl = Controller(EchoOperator(), DictState(), trace_store=store)
        ctrl.step(_sig(1))
        ctrl.step(_sig(2))
        self.assertEqual(len(store), 2)

    def test_traces_accessor_returns_from_store(self):
        store = MemoryTraceStore()
        ctrl = Controller(EchoOperator(), DictState(), trace_store=store)
        ctrl.step(_sig(1))
        ctrl.step(_sig(2))
        ctrl.step(_sig(3))
        self.assertEqual(len(ctrl.traces()), 3)
        self.assertEqual(len(ctrl.traces(last_n=2)), 2)
        self.assertEqual(ctrl.traces(last_n=2)[0].t, 1)

    def test_traces_without_store_returns_empty(self):
        ctrl = Controller(EchoOperator(), DictState())
        ctrl.step(_sig(1))
        self.assertEqual(ctrl.traces(), [])


class TestControllerReplaceOperator(unittest.TestCase):
    def test_replace_operator(self):
        ctrl = Controller(EchoOperator(), DictState())
        action1, _ = ctrl.step(_sig(3))
        self.assertEqual(action1.tag, "echo")

        ctrl.replace_operator(DoubleOperator())
        action2, trace = ctrl.step(_sig(3))
        self.assertEqual(action2.tag, "double")
        self.assertEqual(action2.payload, {"value": 6})
        self.assertEqual(trace.operator_id, "double")


class TestControllerResetState(unittest.TestCase):
    def test_reset_state(self):
        ctrl = Controller(EchoOperator(), DictState({"a": 1}))
        ctrl.step(_sig(None))
        ctrl.reset_state(DictState({"b": 2}))
        self.assertEqual(ctrl.state, DictState({"b": 2}))

    def test_reset_state_enforces_cap(self):
        ctrl = Controller(EchoOperator(), DictState(), state_cap_bytes=32)
        with self.assertRaises(StateSizeError):
            ctrl.reset_state(DictState({"k" * 100: "v" * 100}))


class TestStateCap(unittest.TestCase):
    def test_initial_state_cap_enforced(self):
        with self.assertRaises(StateSizeError):
            Controller(EchoOperator(), DictState({"k" * 100: "v" * 100}), state_cap_bytes=16)

    def test_step_rejects_oversized_output_state(self):
        class BloatOperator:
            operator_id = "bloat"
            version = "1"

            def apply(self, state, signal):
                return DictState({"big": "x" * 5000}), Action(tag="bloat")

            def serialize(self):
                return {}

            @classmethod
            def deserialize(cls, payload):
                return cls()

        ctrl = Controller(BloatOperator(), DictState(), state_cap_bytes=128)
        with self.assertRaises(StateSizeError):
            ctrl.step(_sig(None))

    def test_state_under_cap_passes(self):
        ctrl = Controller(EchoOperator(), DictState({"x": 1}), state_cap_bytes=4096)
        action, trace = ctrl.step(_sig("ok"))
        self.assertEqual(action.tag, "echo")


if __name__ == "__main__":
    unittest.main()
