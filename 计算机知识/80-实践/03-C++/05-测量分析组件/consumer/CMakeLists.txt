cmake_minimum_required(VERSION 3.20)
project(measurement_consumer LANGUAGES CXX)
find_package(WWLMeasurement 1 CONFIG REQUIRED)
add_executable(consumer main.cpp)
target_link_libraries(consumer PRIVATE WWL::measurement)
include(CTest)
add_test(NAME independent_consumer COMMAND consumer)
add_executable(report_consumer report.cpp)
target_link_libraries(report_consumer PRIVATE WWL::measurement)
add_test(NAME independent_report_consumer COMMAND report_consumer)
add_executable(queue_consumer queue.cpp)
target_link_libraries(queue_consumer PRIVATE WWL::measurement)
add_test(NAME independent_queue_consumer COMMAND queue_consumer)
set_tests_properties(independent_queue_consumer PROPERTIES TIMEOUT 20)

# Finite physical projections consume only the installed public API.
add_executable(physics_consumer physics_readouts.cpp)
target_link_libraries(physics_consumer PRIVATE WWL::measurement)
add_test(NAME finite_physics_consumer COMMAND physics_consumer
  "${CMAKE_CURRENT_SOURCE_DIR}/../data/physics-readouts.txt")
add_test(NAME finite_physics_input_rejections COMMAND ${CMAKE_COMMAND}
  -DCONSUMER=$<TARGET_FILE:physics_consumer>
  -DDATA=${CMAKE_CURRENT_SOURCE_DIR}/../data/physics-readouts.txt
  -DOUTPUT=${CMAKE_CURRENT_BINARY_DIR}/physics-negative
  -P ${CMAKE_CURRENT_SOURCE_DIR}/physics_readouts_cases.cmake)
