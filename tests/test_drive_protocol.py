"""ROS·GPIO·시리얼 장치 없이 주행 노드의 입출력 계약을 검증한다."""

import runpy
import sys
import unittest
from itertools import product
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, call, patch


SRC = Path(__file__).resolve().parents[1] / "catkin_ws" / "src"


class DriveProtocolTests(unittest.TestCase):
    def setUp(self):
        self.ros = Mock(ROSInterruptException=InterruptedError)
        self.gpio = Mock(LOW=0, HIGH=1)
        self.serial = MagicMock()
        modules = {
            "rospy": self.ros,
            "std_msgs": SimpleNamespace(),
            "std_msgs.msg": SimpleNamespace(String=str),
            "RPi": SimpleNamespace(GPIO=self.gpio),
            "RPi.GPIO": self.gpio,
            "serial": self.serial,
        }
        imports = patch.dict(sys.modules, modules)
        imports.start()
        self.addCleanup(imports.stop)

    def test_ir_commands_for_all_five_pin_voltages(self):
        # 키는 왼쪽부터 읽은 실제 전압(1=HIGH). 원본 첫 루프의 출력값이다.
        pins = (16, 13, 11, 18, 21)
        expected = {
            "11111": "start", "01110": "foward",
            "11110": "left", "11100": "left", "11000": "left", "10000": "left",
            "01111": "right", "00111": "right", "00011": "right", "00001": "right",
        }
        publish = self.ros.Publisher.return_value.publish
        with patch("time.sleep"):
            for bits in product("01", repeat=5):
                raw = "".join(bits)
                with self.subTest(voltages=raw):
                    self.gpio.input.side_effect = dict(zip(pins, map(int, bits))).__getitem__
                    self.ros.is_shutdown.side_effect = (False, True)
                    publish.reset_mock()
                    runpy.run_path(str(SRC / "ir_line_tracking/IR.py"), run_name="__main__")
                    publish.assert_called_once_with(expected.get(raw, "stop"))
        self.ros.Publisher.assert_called_with("ctrlCmd", str, queue_size=10)
        self.gpio.setmode.assert_called_with(self.gpio.BOARD)

    def test_radar_only_publishes_complete_detection_lines(self):
        port = self.serial.Serial.return_value.__enter__.return_value
        chunks = [b"0\n", b"1", b"", b"0\n", b"1", b"\r\n", b"1\n", b"\xff\n", b"1"]
        port.readline.side_effect = chunks
        self.ros.is_shutdown.side_effect = [False] * len(chunks) + [True]
        self.ros.get_param.return_value = "/dev/ttyUSB1"
        sent = []
        self.ros.Publisher.return_value.publish.side_effect = (
            lambda cmd: sent.append((port.readline.call_count, cmd))
        )
        runpy.run_path(str(SRC / "radar_stop_bridge/radar_publisher.py"), run_name="__main__")
        self.assertEqual(sent, [(6, "stop"), (7, "stop")])
        self.ros.Publisher.assert_called_once_with("radar", str, queue_size=10)
        self.ros.get_param.assert_called_once_with("~serial_port", "/dev/ttyUSB0")
        self.serial.Serial.assert_called_once_with("/dev/ttyUSB1", 9600, timeout=0.2)

    def test_keyboard_commands_and_quit(self):
        terminal, tty, stdin = Mock(), Mock(), Mock()
        stdin.fileno.return_value = 0
        keys = "iwad xq"
        stdin.read.side_effect = list(keys)
        self.ros.is_shutdown.return_value = False
        with patch.dict(sys.modules, {"termios": terminal, "tty": tty}), patch.object(sys, "stdin", stdin):
            with patch("builtins.print"), self.assertRaises(SystemExit) as exit_event:
                runpy.run_path(str(SRC / "keyboard_teleop/tel.py"), run_name="__main__")

        self.assertEqual(exit_event.exception.code, -1)
        self.ros.Publisher.assert_called_once_with("ctrlCmd", str, queue_size=10)
        commands = ["start", "foward", "left", "right", "stop", "stop", "stop"]
        self.assertEqual(self.ros.Publisher.return_value.publish.call_args_list,
                         [call(command) for command in commands])
        restore = call(0, terminal.TCSADRAIN, terminal.tcgetattr.return_value)
        self.assertEqual(terminal.tcsetattr.call_args_list, [restore] * len(keys))

    def test_motor_subscribers_apply_brakes_and_calibrated_duties(self):
        left, right = Mock(), Mock()
        self.gpio.PWM.side_effect = lambda pin, hz: {13: left, 12: right}[pin]
        levels = {}
        self.gpio.output.side_effect = levels.__setitem__

        def exercise_subscribers():
            callbacks = {}
            for subscription in self.ros.Subscriber.call_args_list:
                topic, message_type, callback = subscription.args
                self.assertIs(message_type, str)
                callbacks[topic] = callback
            # 정지 후 일반 조향 명령은 브레이크를 유지하고 start만 이를 해제한다.
            sequence = [
                ("ctrlCmd", "start", 0, 11, 10),
                ("ctrlCmd", "left", 0, 10, 14),
                ("ctrlCmd", "right", 0, 16, 10),
                ("radar", "0", 0, 16, 10),
                ("radar", "stop", 1, 0, 0),
                ("ctrlCmd", "foward", 1, 11, 10),
                ("radar", "start", 1, 11, 10),
                ("ctrlCmd", "start", 0, 11, 10),
                ("ctrlCmd", "stop", 1, 0, 0),
            ]
            for topic, command, brake, left_duty, right_duty in sequence:
                with self.subTest(topic=topic, command=command):
                    callbacks[topic](SimpleNamespace(data=command))
                    self.assertEqual((levels[20], levels[21]), (brake, brake))
                    self.assertEqual((levels[6], levels[16]), (0, 1))
                    left.ChangeDutyCycle.assert_called_with(left_duty)
                    right.ChangeDutyCycle.assert_called_with(right_duty)

        self.ros.spin.side_effect = exercise_subscribers
        with patch("builtins.print"):
            runpy.run_path(str(SRC / "wheel_motor_control/motor_ctrl.py"), run_name="__main__")
        self.ros.spin.assert_called_once_with()
        self.gpio.setmode.assert_called_once_with(self.gpio.BCM)
        self.gpio.PWM.assert_has_calls([call(13, 1000), call(12, 1000)], any_order=True)
        left.stop.assert_called_once_with()
        right.stop.assert_called_once_with()
        self.gpio.cleanup.assert_called_once_with()
