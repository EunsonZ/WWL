cmake_minimum_required(VERSION 3.24)
project(raii_tensor_buffer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

function(enable_project_warnings target)
  if(MSVC)
    target_compile_options(${target} PRIVATE /W4)
  elseif(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic)
  endif()
endfunction()

add_executable(tensor_demo main.cpp)
enable_project_warnings(tensor_demo)

add_executable(tensor_tests tests.cpp)
enable_project_warnings(tensor_tests)

enable_testing()
add_test(NAME tensor_tests COMMAND tensor_tests)
