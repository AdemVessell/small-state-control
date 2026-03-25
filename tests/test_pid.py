import unittest

from small_state_control import Controller, DictState, MemoryTraceStore, Signal
from small_state_control.operators.pid import PIDOperator


class TestPIDProportional(unittest.TestCase):
    def test_pure_p_positive_error(self):
        op = PIDOperator(kp=2.0, ki=0.0, kd=0.0, setpoint=10.0)
        state = DictState({"integral": 0.0, "prev_error": 0.0, "t_last": 0.0})
        sig = Signal(t=1.0, channel="temperature", value=7.0)
        _, action = op.apply(state, sig)
        # error = 10 - 7 = 3, output = 2*3 = 6
        self.assertAlmostEqual(action.payload["error"], 3.0)
        self.assertAlmostEqual(action.payload["output"], 1.0)  # clamped to output_max=1.0

    def test_pure_p_at_setpoint(self):
        op = PIDOperator(kp=5.0, ki=0.0, kd=0.0, setpoint=1.0)
        state = DictState({"integral": 0.0, "prev_error": 0.0, "t_last": 0.0})
        sig = Signal(t=1.0, channel="temp", value=1.0)
        _, action = op.apply(state, sig)
        self.assertAlmostEqual(action.payload["output"], 0.0)

    def test_pure_p_negative_error(self):
        op = PIDOperator(kp=1.0, setpoint=5.0, output_min=-10.0, output_max=10.0)
        state = DictState({"integral": 0.0, "prev_error": 0.0, "t_last": 0.0})
        sig = Signal(t=1.0, channel="temp", value=8.0)
        _, action = op.apply(state, sig)
        self.assertAlmostEqual(action.payload["output"], -3.0)


class TestPIDIntegral(unittest.TestCase):
    def test_integral_accumulates(self):
        op = PIDOperator(kp=0.0, ki=1.0, kd=0.0, setpoint=10.0, output_min=-100, output_max=100)
        state = DictState({"integral": 0.0, "prev_error": 0.0, "t_last": 0.0})

        # step 1: t=1, value=8, error=2, dt=1, integral=0+2*1=2
        new_state, action = op.apply(state, Signal(t=1.0, channel="temp", value=8.0))
        self.assertAlmostEqual(new_state.data["integral"], 2.0)
        self.assertAlmostEqual(action.payload["i"], 2.0)

        # step 2: t=2, value=9, error=1, dt=1, integral=2+1*1=3
        new_state2, action2 = op.apply(new_state, Signal(t=2.0, channel="temp", value=9.0))
        self.assertAlmostEqual(new_state2.data["integral"], 3.0)
        self.assertAlmostEqual(action2.payload["i"], 3.0)

    def test_integral_anti_windup(self):
        op = PIDOperator(ki=1.0, setpoint=100.0, integral_min=-5, integral_max=5, output_max=1000)
        state = DictState({"integral": 4.5, "prev_error": 0.0, "t_last": 0.0})
        sig = Signal(t=1.0, channel="temp", value=0.0)
        # error=100, integral=4.5+100*1=104.5 → clamped to 5
        new_state, _ = op.apply(state, sig)
        self.assertAlmostEqual(new_state.data["integral"], 5.0)


class TestPIDDerivative(unittest.TestCase):
    def test_derivative_responds_to_error_change(self):
        op = PIDOperator(kp=0.0, ki=0.0, kd=1.0, setpoint=10.0, output_min=-100, output_max=100)
        state = DictState({"integral": 0.0, "prev_error": 2.0, "t_last": 0.0})
        sig = Signal(t=1.0, channel="temp", value=5.0)
        # error = 10-5 = 5, deriv = (5-2)/1 = 3
        _, action = op.apply(state, sig)
        self.assertAlmostEqual(action.payload["d"], 3.0)


class TestPIDBounds(unittest.TestCase):
    def test_output_clamped_high(self):
        op = PIDOperator(kp=100.0, setpoint=10.0, output_max=5.0)
        state = DictState({"integral": 0.0, "prev_error": 0.0, "t_last": 0.0})
        sig = Signal(t=1.0, channel="temp", value=0.0)
        _, action = op.apply(state, sig)
        self.assertAlmostEqual(action.payload["output"], 5.0)

    def test_output_clamped_low(self):
        op = PIDOperator(kp=100.0, setpoint=0.0, output_min=-3.0)
        state = DictState({"integral": 0.0, "prev_error": 0.0, "t_last": 0.0})
        sig = Signal(t=1.0, channel="temp", value=10.0)
        _, action = op.apply(state, sig)
        self.assertAlmostEqual(action.payload["output"], -3.0)


class TestPIDSerialization(unittest.TestCase):
    def test_roundtrip(self):
        op = PIDOperator(kp=2.5, ki=0.1, kd=0.05, setpoint=42.0, output_min=-10, output_max=10)
        payload = op.serialize()
        op2 = PIDOperator.deserialize(payload)
        self.assertEqual(op.serialize(), op2.serialize())

    def test_all_keys_present(self):
        payload = PIDOperator().serialize()
        for key in ("kp", "ki", "kd", "setpoint", "output_min", "output_max", "integral_min", "integral_max"):
            self.assertIn(key, payload)


class TestPIDWithController(unittest.TestCase):
    def test_convergence_toward_setpoint(self):
        """PI controller driving a simulated first-order plant toward setpoint."""
        store = MemoryTraceStore()
        op = PIDOperator(kp=1.0, ki=0.5, kd=0.0, setpoint=1.0, output_min=-5, output_max=5, integral_max=20)
        ctrl = Controller(op, DictState({"integral": 0.0, "prev_error": 0.0, "t_last": 0.0}), "pid-ctrl", trace_store=store)

        pv = 0.0
        for i in range(80):
            action, _ = ctrl.step(Signal(t=float(i), channel="plant", value=pv))
            # simple first-order plant: pv moves toward output
            pv = pv + 0.1 * action.payload["output"]

        # after 80 steps the plant should be near setpoint
        self.assertAlmostEqual(pv, 1.0, delta=0.1)
        self.assertEqual(len(store), 80)


if __name__ == "__main__":
    unittest.main()
