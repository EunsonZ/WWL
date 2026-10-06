cmake_minimum_required(VERSION 3.20)
project(cache_locality_lab LANGUAGES CXX)

include(CTest)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(cache_locality cache_locality.cpp)
if(MSVC)
  target_compile_options(cache_locality PRIVATE /W4 /permissive-)
else()
  target_compile_options(cache_locality PRIVATE -Wall -Wextra -Wpedantic)
endif()

if(BUILD_TESTING)
  add_test(NAME cache_locality_self_test COMMAND cache_locality --self-test)
endif()
