cmake_minimum_required(VERSION 3.0.2)
project(radar)

find_package(catkin REQUIRED)
catkin_package()

catkin_install_python(PROGRAMS src/radar_publisher.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
