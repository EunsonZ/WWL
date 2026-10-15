cmake_minimum_required(VERSION 3.20)
project(data_representation_alignment_lab LANGUAGES CXX)

include(CTest)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(data_representation data_representation.cpp)
if(MSVC)
  target_compile_options(data_representation PRIVATE /W4 /permissive-)
else()
  target_compile_options(data_representation PRIVATE -Wall -Wextra -Wpedantic)
endif()

if(BUILD_TESTING)
  add_test(NAME data_representation_self_test COMMAND data_representation --self-test)
endif()
