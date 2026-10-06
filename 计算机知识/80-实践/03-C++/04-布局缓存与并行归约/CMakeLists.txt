cmake_minimum_required(VERSION 3.20)
project(cpp_layout_cache_lab LANGUAGES CXX)

include(CTest)
find_package(Threads REQUIRED)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

function(enable_lab_warnings target)
  if(MSVC)
    target_compile_options(${target} PRIVATE /W4 /permissive-)
  else()
    target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic)
  endif()
endfunction()

add_executable(layout_benchmark layout_benchmark.cpp)
target_link_libraries(layout_benchmark PRIVATE Threads::Threads)
enable_lab_warnings(layout_benchmark)

add_executable(layout_tests layout_tests.cpp)
target_link_libraries(layout_tests PRIVATE Threads::Threads)
enable_lab_warnings(layout_tests)

if(BUILD_TESTING)
  add_test(NAME layout_tests COMMAND layout_tests)
endif()
