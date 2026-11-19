cmake_minimum_required(VERSION 3.0.2)
project(motor)

find_package(catkin REQUIRED)
catkin_package()

catkin_install_python(PROGRAMS motor_ctrl.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
