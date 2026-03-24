import unittest

from small_state_control import Controller


class EchoOperator:
    """Echoes signal into action, passes state through unchanged."""

    operator_id = "echo"

    def apply(self, signal, state):
        return dict(state), dict(signal)


class DoubleOperator:
    """Doubles every numeric value in the signal."""

    operator_id = "double"

    def apply(self, signal, state):
        return state, {k: v * 2 for k, v in signal.items()}


class TestController(unittest.TestCase):
    def test_step_returns_action_and_trace(self):
        ctrl = Controller("c1", {"x": 0}, EchoOperator())
        action, trace = ctrl.step({"msg": "hello"})

        self.assertEqual(action, {"msg": "hello"})
        self.assertEqual(trace.t, 0)
        self.assertEqual(trace.controller_id, "c1")
        self.assertEqual(trace.operator_id, "echo")
        self.assertEqual(trace.signal, {"msg": "hello"})
        self.assertEqual(trace.state_before, {"x": 0})
        self.assertEqual(trace.state_after, {"x": 0})
        self.assertEqual(trace.action, {"msg": "hello"})
        self.assertEqual(trace.meta, {})

    def test_step_increments_t(self):
        ctrl = Controller("c1", {}, EchoOperator())
        _, t0 = ctrl.step({"a": 1})
        _, t1 = ctrl.step({"b": 2})
        self.assertEqual(t0.t, 0)
        self.assertEqual(t1.t, 1)

    def test_state_progresses(self):
        class CountOperator:
            operator_id = "count"

            def apply(self, signal, state):
                n = state.get("n", 0) + 1
                return {"n": n}, {"count": n}

        ctrl = Controller("c1", {"n": 0}, CountOperator())
        a1, _ = ctrl.step({})
        a2, _ = ctrl.step({})
        self.assertEqual(a1, {"count": 1})
        self.assertEqual(a2, {"count": 2})
        self.assertEqual(ctrl.state, {"n": 2})

    def test_operator_hot_swap(self):
        ctrl = Controller("c1", {}, EchoOperator())
        action1, _ = ctrl.step({"v": 3})
        self.assertEqual(action1, {"v": 3})

        ctrl.operator = DoubleOperator()
        action2, trace = ctrl.step({"v": 3})
        self.assertEqual(action2, {"v": 6})
        self.assertEqual(trace.operator_id, "double")

    def test_state_mutation_isolation(self):
        """Operator mutating its input must not corrupt controller state."""

        class MutatingOperator:
            operator_id = "mutator"

            def apply(self, signal, state):
                state["dirty"] = True  # mutates the copy, not real state
                return {"clean": True}, {}

        ctrl = Controller("c1", {"x": 1}, MutatingOperator())
        ctrl.step({})
        self.assertEqual(ctrl.state, {"clean": True})
        self.assertNotIn("dirty", ctrl.state)


if __name__ == "__main__":
    unittest.main()
