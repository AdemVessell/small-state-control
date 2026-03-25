import math
import unittest

from small_state_control import Controller, DictState, MemoryTraceStore, Signal
from small_state_control.operators.dife import DIFEOperator


class TestDIFEEquation(unittest.TestCase):
    def test_zero_signal_produces_decay_only(self):
        op = DIFEOperator(lam=1.0, threshold=1.0, decay=0.9, gain=0.1)
        state = DictState({"budget": 0.5, "t_last": 0.0})
        sig = Signal(t=1.0, channel="loss", value=0.0)
        new_state, action = op.apply(state, sig)
        # weight = exp(-1*1) * 0.0 = 0
        # budget = 0.5 * 0.9 + 0 = 0.45
        self.assertAlmostEqual(new_state.data["budget"], 0.45, places=5)
        self.assertAlmostEqual(action.payload["fraction"], 0.45, places=5)

    def test_full_signal_at_zero_dt(self):
        op = DIFEOperator(lam=1.0, threshold=1.0, decay=0.9, gain=0.2)
        state = DictState({"budget": 0.0, "t_last": 5.0})
        sig = Signal(t=5.0, channel="loss", value=1.0)
        new_state, action = op.apply(state, sig)
        # dt=0 → weight = exp(0)*1.0 = 1.0
        # budget = 0.0*0.9 + 1.0*0.2 = 0.2
        self.assertAlmostEqual(new_state.data["budget"], 0.2, places=5)

    def test_exponential_decay_over_time(self):
        op = DIFEOperator(lam=2.0, threshold=1.0, decay=1.0, gain=1.0)
        state = DictState({"budget": 0.0, "t_last": 0.0})
        sig = Signal(t=1.0, channel="loss", value=1.0)
        _, action = op.apply(state, sig)
        expected = math.exp(-2.0)
        self.assertAlmostEqual(action.payload["fraction"], expected, places=5)

    def test_budget_clamped_to_ceiling(self):
        op = DIFEOperator(decay=1.0, gain=2.0, ceiling=0.8)
        state = DictState({"budget": 0.7, "t_last": 0.0})
        sig = Signal(t=0.0, channel="loss", value=1.0)
        new_state, _ = op.apply(state, sig)
        self.assertAlmostEqual(new_state.data["budget"], 0.8, places=5)

    def test_budget_clamped_to_floor(self):
        op = DIFEOperator(decay=0.0, gain=0.0, floor=0.05)
        state = DictState({"budget": 0.5, "t_last": 0.0})
        sig = Signal(t=0.0, channel="loss", value=0.0)
        new_state, _ = op.apply(state, sig)
        self.assertAlmostEqual(new_state.data["budget"], 0.05, places=5)

    def test_negative_signal_clamped_to_zero(self):
        op = DIFEOperator(decay=0.5, gain=1.0)
        state = DictState({"budget": 0.4, "t_last": 0.0})
        sig = Signal(t=0.0, channel="loss", value=-5.0)
        new_state, _ = op.apply(state, sig)
        # normed = clamp(-5/1, 0, 1) = 0 → weight = 0
        # budget = 0.4*0.5 = 0.2
        self.assertAlmostEqual(new_state.data["budget"], 0.2, places=5)

    def test_t_last_updates(self):
        op = DIFEOperator()
        state = DictState({"budget": 0.0, "t_last": 3.0})
        sig = Signal(t=7.0, channel="loss", value=0.5)
        new_state, _ = op.apply(state, sig)
        self.assertEqual(new_state.data["t_last"], 7.0)


class TestDIFESerialization(unittest.TestCase):
    def test_roundtrip(self):
        op = DIFEOperator(lam=2.5, threshold=0.8, decay=0.92, gain=0.15, floor=0.01, ceiling=0.9)
        payload = op.serialize()
        op2 = DIFEOperator.deserialize(payload)
        self.assertEqual(op.serialize(), op2.serialize())

    def test_serialize_contains_all_params(self):
        op = DIFEOperator()
        payload = op.serialize()
        for key in ("lam", "threshold", "decay", "gain", "floor", "ceiling"):
            self.assertIn(key, payload)


class TestDIFEWithController(unittest.TestCase):
    def test_multi_step_budget_trajectory(self):
        store = MemoryTraceStore()
        op = DIFEOperator(lam=0.5, threshold=1.0, decay=0.9, gain=0.2)
        ctrl = Controller(op, DictState({"budget": 0.0, "t_last": 0.0}), "dife-ctrl", trace_store=store)

        budgets = []
        for i in range(10):
            action, _ = ctrl.step(Signal(t=float(i), channel="loss", value=0.8))
            budgets.append(action.payload["fraction"])

        # budget should rise from 0 and approach a steady state
        self.assertGreater(budgets[-1], budgets[0])
        # should remain bounded
        for b in budgets:
            self.assertGreaterEqual(b, 0.0)
            self.assertLessEqual(b, 1.0)
        # traces recorded
        self.assertEqual(len(store), 10)


if __name__ == "__main__":
    unittest.main()
