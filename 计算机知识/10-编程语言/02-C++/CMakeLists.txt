cmake_minimum_required(VERSION 3.20)
project(cpp_learning_examples LANGUAGES CXX)

include(CTest)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

function(enable_course_warnings target)
  if(MSVC)
    target_compile_options(${target} PRIVATE /W4 /permissive-)
  else()
    target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic)
  endif()
endfunction()

# stl.cpp 已退役，保留笔记中的历史片段，不再创建缺失源码目标。
foreach(example IN ITEMS toolchain types_functions lifetime raii move errors concurrency layout)
  add_executable(${example} ${example}.cpp)
  enable_course_warnings(${example})
  if(BUILD_TESTING)
    add_test(NAME ${example} COMMAND ${example})
  endif()
endforeach()

find_package(Threads REQUIRED)
target_link_libraries(concurrency PRIVATE Threads::Threads)
