cmake_minimum_required(VERSION 3.20)
project(memory_translation_topology_lab LANGUAGES CXX)

include(CTest)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(arena_accounting arena_accounting.cpp)
if(MSVC)
  target_compile_options(arena_accounting PRIVATE /W4 /permissive-)
else()
  target_compile_options(arena_accounting PRIVATE -Wall -Wextra -Wpedantic)
endif()

if(BUILD_TESTING)
  add_test(NAME arena_accounting_self_test COMMAND arena_accounting --self-test)

  find_package(Python3 COMPONENTS Interpreter QUIET)
  if(Python3_Interpreter_FOUND)
    add_test(
      NAME system_observer_python_tests
      COMMAND "${Python3_EXECUTABLE}" -m unittest -v test_system_observer.py
    )
    set_tests_properties(
      system_observer_python_tests
      PROPERTIES WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
    )
  else()
    message(STATUS "SKIP: Python3 interpreter unavailable; Python observer tests not registered")
  endif()
endif()
