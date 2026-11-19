#!/usr/bin/env python3
"""Arduino가 보낸 감지 신호를 ROS의 radar 토픽으로 전달한다."""

import rospy
import serial
from std_msgs.msg import String


def publish_data():
    rospy.init_node("data_publisher", anonymous=True)
    publisher = rospy.Publisher("radar", String, queue_size=10)
    port_name = rospy.get_param("~serial_port", "/dev/ttyUSB0")

    # 타임아웃은 장치가 조용할 때도 ROS 종료 요청을 확인하기 위한 것이다.
    with serial.Serial(port_name, 9600, timeout=0.2) as port:
        line = bytearray()
        while not rospy.is_shutdown():
            line.extend(port.readline())
            if not line.endswith(b"\n"):
                continue  # 다음 읽기에서 줄의 나머지가 도착할 수 있다.

            # Arduino의 "1" 한 줄마다 정지 1회. "0"에서는 명령을 보내지 않는다.
            if line.strip() == b"1":
                publisher.publish("stop")
            line.clear()


if __name__ == "__main__":
    try:
        publish_data()
    except rospy.ROSInterruptException:
        pass
