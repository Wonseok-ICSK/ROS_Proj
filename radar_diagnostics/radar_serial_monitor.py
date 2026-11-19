"""ROS 없이 Arduino 레이더의 한 줄 출력을 확인한다."""

from time import sleep

import serial


def main():
    # 펌웨어가 줄바꿈을 포함해 보낸 '0' 또는 '1'을 그대로 출력한다.
    with serial.Serial("/dev/ttyUSB0", 9600) as port:
        while True:
            print(port.readline().decode(), end="")
            sleep(0.1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
