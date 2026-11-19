cmake_minimum_required(VERSION 3.0.2)
project(teleop_key)

find_package(catkin REQUIRED)
catkin_package()

catkin_install_python(PROGRAMS src/tel.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
