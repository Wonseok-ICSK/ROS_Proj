#!/usr/bin/env python3
"""ROS 주행 명령과 레이더 정지 신호를 좌우 모터의 GPIO 출력으로 변환한다."""

from contextlib import ExitStack
from threading import Lock

import RPi.GPIO as GPIO
import rospy
from std_msgs.msg import String


# BCM 번호이며, PWM 주파수의 단위는 Hz이다.
LEFT_PWM_PIN, RIGHT_PWM_PIN = 13, 12
LEFT_DIR_PIN, RIGHT_DIR_PIN = 6, 16
LEFT_BRAKE_PIN, RIGHT_BRAKE_PIN = 20, 21
PWM_FREQUENCY = 1000

# 왼쪽·오른쪽 듀티비(%)는 원래 차체의 직진 보정과 회전 속도 차를 반영한다.
# IR·키보드 노드가 보내는 전진 명령의 철자는 'foward'이다.
DRIVE_DUTIES = {"foward": (11, 10), "left": (10, 14), "right": (16, 10)}


class MotorDriver:
    def __init__(self, left_pwm, right_pwm):
        self.left_pwm = left_pwm
        self.right_pwm = right_pwm
        self.lock = Lock()
        self.active = True

    def set_brakes(self, level):
        GPIO.output(LEFT_BRAKE_PIN, level)
        GPIO.output(RIGHT_BRAKE_PIN, level)

    def set_duties(self, left, right):
        self.left_pwm.ChangeDutyCycle(left)
        self.right_pwm.ChangeDutyCycle(right)

    def on_command(self, message):
        # 두 토픽의 콜백은 다른 스레드에서 실행될 수 있다. 한 명령의 출력을 함께 적용한다.
        with self.lock:
            if not self.active:
                return

            command = message.data
            if command == "stop":
                self.set_duties(0, 0)
                self.set_brakes(GPIO.HIGH)
                return

            if command == "start":
                # 정지 후 브레이크를 해제하는 명령은 start뿐이며, 해제 직후 전진한다.
                self.set_brakes(GPIO.LOW)
                self.set_duties(0, 0)
                command = "foward"

            if command in DRIVE_DUTIES:
                # 같은 전진 방향에서도 좌우 모터의 방향 핀 극성은 반대다.
                GPIO.output(LEFT_DIR_PIN, GPIO.LOW)
                GPIO.output(RIGHT_DIR_PIN, GPIO.HIGH)
                self.set_duties(*DRIVE_DUTIES[command])

    def on_radar(self, message):
        if message.data == "stop":
            self.on_command(message)
            print("stop")

    def deactivate(self):
        with self.lock:
            self.active = False


def main():
    rospy.init_node("motorDriver", anonymous=True)
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    # 초기화 중 실패하거나 ROS가 종료되어도 이미 확보한 PWM과 GPIO를 해제한다.
    with ExitStack() as resources:
        resources.callback(GPIO.cleanup)
        for pin in (LEFT_PWM_PIN, LEFT_DIR_PIN, RIGHT_PWM_PIN, RIGHT_DIR_PIN,
                    LEFT_BRAKE_PIN, RIGHT_BRAKE_PIN):
            GPIO.setup(pin, GPIO.OUT)

        left_pwm = GPIO.PWM(LEFT_PWM_PIN, PWM_FREQUENCY)
        left_pwm.start(0)
        resources.callback(left_pwm.stop)
        right_pwm = GPIO.PWM(RIGHT_PWM_PIN, PWM_FREQUENCY)
        right_pwm.start(0)
        resources.callback(right_pwm.stop)

        driver = MotorDriver(left_pwm, right_pwm)
        # ExitStack은 역순으로 실행하므로 콜백을 막은 다음 PWM을 정리한다.
        resources.callback(driver.deactivate)
        rospy.Subscriber("ctrlCmd", String, driver.on_command)
        rospy.Subscriber("radar", String, driver.on_radar)
        rospy.spin()


if __name__ == "__main__":
    try:
        main()
    except (EOFError, rospy.ROSInterruptException):
        pass
