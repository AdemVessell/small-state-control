import unittest

from small_state_control import Controller, DictState, MemoryTraceStore, Signal
from small_state_control.operators.aimd import AIMDBudgetOperator


class TestAIMDLogic(unittest.TestCase):
    def test_additive_increase_below_threshold(self):
        op = AIMDBudgetOperator(additive_inc=0.1, pressure_threshold=0.5)
        state = DictState({"budget": 0.3})
        sig = Signal(t=0.0, channel="pressure", value=0.2)
        new_state, action = op.apply(state, sig)
        self.assertAlmostEqual(new_state.data["budget"], 0.4, places=5)
        self.assertEqual(action.tag, "increase")

    def test_multiplicative_decrease_at_threshold(self):
        op = AIMDBudgetOperator(multiplicative_dec=0.5, pressure_threshold=0.5)
        state = DictState({"budget": 0.8})
        sig = Signal(t=0.0, channel="pressure", value=0.5)
        new_state, action = op.apply(state, sig)
        self.assertAlmostEqual(new_state.data["budget"], 0.4, places=5)
        self.assertEqual(action.tag, "decrease")

    def test_multiplicative_decrease_above_threshold(self):
        op = AIMDBudgetOperator(multiplicative_dec=0.25, pressure_threshold=0.5)
        state = DictState({"budget": 1.0})
        sig = Signal(t=0.0, channel="pressure", value=0.9)
        new_state, action = op.apply(state, sig)
        self.assertAlmostEqual(new_state.data["budget"], 0.25, places=5)

    def test_ceiling_enforced(self):
        op = AIMDBudgetOperator(additive_inc=0.5, ceiling=0.6)
        state = DictState({"budget": 0.5})
        sig = Signal(t=0.0, channel="pressure", value=0.0)
        new_state, _ = op.apply(state, sig)
        self.assertAlmostEqual(new_state.data["budget"], 0.6, places=5)

    def test_floor_enforced(self):
        op = AIMDBudgetOperator(multiplicative_dec=0.1, floor=0.05, pressure_threshold=0.5)
        state = DictState({"budget": 0.1})
        sig = Signal(t=0.0, channel="pressure", value=1.0)
        new_state, _ = op.apply(state, sig)
        self.assertAlmostEqual(new_state.data["budget"], 0.05, places=5)

    def test_default_budget_from_floor(self):
        op = AIMDBudgetOperator(floor=0.02)
        state = DictState({})  # no budget key
        sig = Signal(t=0.0, channel="pressure", value=0.0)
        new_state, _ = op.apply(state, sig)
        self.assertGreaterEqual(new_state.data["budget"], 0.02)


class TestAIMDSerialization(unittest.TestCase):
    def test_roundtrip(self):
        op = AIMDBudgetOperator(additive_inc=0.05, multiplicative_dec=0.3, floor=0.01, ceiling=0.95, pressure_threshold=0.7)
        payload = op.serialize()
        op2 = AIMDBudgetOperator.deserialize(payload)
        self.assertEqual(op.serialize(), op2.serialize())

    def test_all_keys_present(self):
        payload = AIMDBudgetOperator().serialize()
        for key in ("additive_inc", "multiplicative_dec", "floor", "ceiling", "pressure_threshold"):
            self.assertIn(key, payload)


class TestAIMDWithController(unittest.TestCase):
    def test_sawtooth_behavior(self):
        """Low pressure → budget rises; high pressure → budget drops."""
        store = MemoryTraceStore()
        op = AIMDBudgetOperator(additive_inc=0.1, multiplicative_dec=0.5, ceiling=1.0, pressure_threshold=0.5)
        ctrl = Controller(op, DictState({"budget": 0.0}), "aimd-ctrl", trace_store=store)

        # 5 steps of low pressure → budget should climb
        for i in range(5):
            ctrl.step(Signal(t=float(i), channel="pressure", value=0.1))
        peak = ctrl.state.data["budget"]
        self.assertGreater(peak, 0.3)

        # 1 step of high pressure → budget should drop
        ctrl.step(Signal(t=5.0, channel="pressure", value=0.9))
        after_drop = ctrl.state.data["budget"]
        self.assertLess(after_drop, peak)

        self.assertEqual(len(store), 6)


if __name__ == "__main__":
    unittest.main()
