import unittest

from small_state_control import Controller, DictState, MemoryTraceStore, Signal
from small_state_control.operators.aimd import AIMDBudgetOperator
from small_state_control.operators.compose import SequenceOperator
from small_state_control.operators.dife import DIFEOperator


class TestSequenceOperator(unittest.TestCase):
    def test_requires_at_least_two(self):
        with self.assertRaises(ValueError):
            SequenceOperator([DIFEOperator()])

    def test_state_flows_through(self):
        """DIFE writes budget+t_last; AIMD reads budget.
        Proves state flows from op[0] output to op[1] input."""
        dife = DIFEOperator(lam=0.0, threshold=1.0, decay=0.0, gain=0.5)
        aimd = AIMDBudgetOperator(additive_inc=0.1, pressure_threshold=0.5)
        seq = SequenceOperator([dife, aimd])

        state = DictState({"budget": 0.0, "t_last": 0.0})
        sig = Signal(t=0.0, channel="loss", value=1.0)
        new_state, action = seq.apply(state, sig)

        # DIFE: budget = 0.0*0.0 + 1.0*0.5 = 0.5, t_last = 0.0
        # AIMD sees budget=0.5, pressure=1.0 (value) but wait—
        # signal.value=1.0 which is the *loss*, AIMD reads it as pressure.
        # pressure=1.0 >= 0.5 threshold → decrease: 0.5 * 0.5 = 0.25
        self.assertAlmostEqual(new_state.data["budget"], 0.25, places=5)
        self.assertEqual(action.tag, "sequence")
        self.assertEqual(len(action.payload["steps"]), 2)

    def test_actions_collected(self):
        dife = DIFEOperator()
        aimd = AIMDBudgetOperator()
        seq = SequenceOperator([dife, aimd])

        state = DictState({"budget": 0.0, "t_last": 0.0})
        sig = Signal(t=0.0, channel="test", value=0.5)
        _, action = seq.apply(state, sig)

        steps = action.payload["steps"]
        self.assertEqual(steps[0]["tag"], "replay")
        self.assertIn(steps[1]["tag"], ("increase", "decrease"))

    def test_serialization(self):
        dife = DIFEOperator(lam=2.0)
        aimd = AIMDBudgetOperator(additive_inc=0.05)
        seq = SequenceOperator([dife, aimd], seq_id="my-seq")
        payload = seq.serialize()

        self.assertEqual(payload["operator_id"], "my-seq")
        self.assertEqual(len(payload["operators"]), 2)
        self.assertEqual(payload["operators"][0]["operator_id"], "dife")
        self.assertEqual(payload["operators"][1]["operator_id"], "aimd")

    def test_deserialize_raises(self):
        with self.assertRaises(NotImplementedError):
            SequenceOperator.deserialize({})


class TestComposedController(unittest.TestCase):
    def test_multi_step_composed_trajectory(self):
        store = MemoryTraceStore()
        dife = DIFEOperator(lam=0.1, threshold=1.0, decay=0.9, gain=0.15)
        aimd = AIMDBudgetOperator(additive_inc=0.02, multiplicative_dec=0.5, pressure_threshold=0.6)
        seq = SequenceOperator([dife, aimd])

        ctrl = Controller(
            seq,
            DictState({"budget": 0.0, "t_last": 0.0}),
            "composed-ctrl",
            trace_store=store,
        )

        # Simulate 20 steps: loss oscillates
        for i in range(20):
            loss = 0.3 if i % 4 < 2 else 0.8
            ctrl.step(Signal(t=float(i), channel="loss", value=loss))

        self.assertEqual(len(store), 20)
        # budget should be bounded
        b = ctrl.state.data["budget"]
        self.assertGreaterEqual(b, 0.0)
        self.assertLessEqual(b, 1.0)

    def test_trace_records_composite_operator_id(self):
        store = MemoryTraceStore()
        seq = SequenceOperator(
            [DIFEOperator(), AIMDBudgetOperator()],
            seq_id="dife+aimd",
        )
        ctrl = Controller(seq, DictState({"budget": 0.0, "t_last": 0.0}), "c", trace_store=store)
        ctrl.step(Signal(t=0.0, channel="x", value=0.5))
        trace = store.get()[0]
        self.assertEqual(trace.operator_id, "dife+aimd")


if __name__ == "__main__":
    unittest.main()
