#!/usr/bin/env python3
"""대화형 터미널에서 한 글자씩 읽어 ctrlCmd 토픽에 주행 명령을 보낸다."""

import sys
import termios
import tty

import rospy
from std_msgs.msg import String


# 'foward'는 모터 노드가 구독하는 기존 명령 문자열이다.
KEY_COMMANDS = {"w": "foward", "a": "left", "d": "right", "i": "start"}


def get_key():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        # Enter를 기다리지 않고 읽고, 예외가 발생해도 터미널 모드를 복원한다.
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def direction_publisher():
    rospy.init_node("direction_publisher", anonymous=True)
    publisher = rospy.Publisher("ctrlCmd", String, queue_size=10)
    rate = rospy.Rate(10)

    while not rospy.is_shutdown():
        key = get_key()
        # q와 지정되지 않은 키는 모두 정지를 발행하고, q만 노드를 종료한다.
        command = KEY_COMMANDS.get(key, "stop")
        publisher.publish(command)
        if key == "q":
            print("end")
            return -1
        print("init" if key == "i" else command)
        rate.sleep()


if __name__ == "__main__":
    try:
        sys.exit(direction_publisher())
    except rospy.ROSInterruptException:
        pass
