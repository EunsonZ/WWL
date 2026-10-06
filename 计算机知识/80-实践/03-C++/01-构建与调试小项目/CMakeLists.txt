cmake_minimum_required(VERSION 3.24)
project(cpp_build_debug LANGUAGES CXX)

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

add_library(word_counter_lib word_counter.cpp)
target_include_directories(word_counter_lib PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}")
enable_project_warnings(word_counter_lib)

add_executable(word_counter main.cpp)
target_link_libraries(word_counter PRIVATE word_counter_lib)
enable_project_warnings(word_counter)

add_executable(word_counter_tests tests.cpp)
target_link_libraries(word_counter_tests PRIVATE word_counter_lib)
enable_project_warnings(word_counter_tests)

enable_testing()
add_test(NAME word_counter_tests COMMAND word_counter_tests)
