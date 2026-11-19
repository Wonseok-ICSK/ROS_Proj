#!/usr/bin/env python3
"""다섯 IR 센서의 감지 패턴을 모터 제어 명령으로 변환한다."""

from time import sleep

import RPi.GPIO as GPIO
import rospy
from std_msgs.msg import String


# 센서의 왼쪽 끝부터 오른쪽 끝까지 라즈베리파이 헤더의 물리 핀 번호(BOARD).
SENSOR_PINS = (16, 13, 11, 18, 21)

# 각 자리는 같은 순서의 센서이며, 1은 입력 전압이 LOW일 때의 감지를 뜻한다.
COMMAND_BY_PATTERN = {
    "00000": "start",
    "10001": "foward",  # motor 노드가 수신하는 기존 명령 철자
    "10000": "right",
    "11000": "right",
    "11100": "right",
    "11110": "right",
    "00001": "left",
    "00011": "left",
    "00111": "left",
    "01111": "left",
}


def tracer():
    rospy.init_node("irLineTracking", anonymous=True)
    publisher = rospy.Publisher("ctrlCmd", String, queue_size=10)

    GPIO.setmode(GPIO.BOARD)
    try:
        GPIO.setup(SENSOR_PINS, GPIO.IN)
        while not rospy.is_shutdown():
            pattern = "".join("0" if GPIO.input(pin) else "1" for pin in SENSOR_PINS)
            command = COMMAND_BY_PATTERN.get(pattern, "stop")
            rospy.logdebug("IR %s -> %s", pattern, command)
            publisher.publish(command)
            sleep(0.1)
    finally:
        GPIO.cleanup(SENSOR_PINS)


if __name__ == "__main__":
    tracer()
