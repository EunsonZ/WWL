cmake_minimum_required(VERSION 3.20)
project(file_descriptor_pipe_lab LANGUAGES CXX)

if(NOT UNIX)
  message(FATAL_ERROR "fd_pipe_demo requires a UNIX/POSIX platform such as macOS or Linux")
endif()

include(CTest)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(fd_pipe_demo fd_pipe_demo.cpp)
if(MSVC)
  target_compile_options(fd_pipe_demo PRIVATE /W4 /permissive-)
else()
  target_compile_options(fd_pipe_demo PRIVATE -Wall -Wextra -Wpedantic)
endif()

if(BUILD_TESTING)
  add_test(NAME fd_pipe_self_test COMMAND fd_pipe_demo --self-test)
endif()
