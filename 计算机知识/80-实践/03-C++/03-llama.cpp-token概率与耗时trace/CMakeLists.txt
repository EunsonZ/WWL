cmake_minimum_required(VERSION 3.24)
project(llama_token_trace LANGUAGES CXX)

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

enable_testing()
add_executable(trace_math_tests trace_math_tests.cpp)
enable_project_warnings(trace_math_tests)
add_test(NAME trace_math_tests COMMAND trace_math_tests)

set(LLAMA_CPP_DIR "" CACHE PATH "Pinned local llama.cpp checkout; it is never fetched automatically")
if(LLAMA_CPP_DIR STREQUAL "")
    message(STATUS "Only trace_math_tests is enabled. Set LLAMA_CPP_DIR to a pinned local checkout to build llama_token_trace.")
    return()
endif()

if(NOT EXISTS "${LLAMA_CPP_DIR}/CMakeLists.txt")
    message(FATAL_ERROR "LLAMA_CPP_DIR is not a llama.cpp source checkout: ${LLAMA_CPP_DIR}")
endif()

add_subdirectory("${LLAMA_CPP_DIR}" llama_cpp_build EXCLUDE_FROM_ALL)
if(NOT TARGET llama)
    message(FATAL_ERROR "Pinned llama.cpp checkout did not export target 'llama'; inspect its CMake API before changing this lesson.")
endif()

add_executable(llama_token_trace llama_token_trace.cpp)
target_link_libraries(llama_token_trace PRIVATE llama)
enable_project_warnings(llama_token_trace)
