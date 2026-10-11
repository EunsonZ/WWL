cmake_minimum_required(VERSION 3.28)
project(WWLMeasurementModule LANGUAGES CXX)
include(CTest)
# Existing package was built and installed with the same selected toolchain.
find_package(WWLMeasurement 1.2 CONFIG REQUIRED)
add_library(measurement_module STATIC wwl.measurement.cpp)
target_sources(measurement_module PUBLIC FILE_SET public_modules TYPE CXX_MODULES
  FILES wwl.measurement.cppm)
target_compile_features(measurement_module PUBLIC cxx_std_20)
set_target_properties(measurement_module PROPERTIES CXX_EXTENSIONS OFF)
target_link_libraries(measurement_module PUBLIC WWL::measurement)
if(NOT MSVC)
  target_compile_options(measurement_module PRIVATE -Wall -Wextra -Wpedantic
    -fno-fast-math -ffp-contract=off)
endif()
add_subdirectory(consumer)
if(BUILD_TESTING)
  if(NOT WWL_REPORT_REFERENCE)
    message(FATAL_ERROR "Set WWL_REPORT_REFERENCE to the existing data/report-reference.txt")
  endif()
  add_test(NAME module_header_same_report COMMAND ${CMAKE_COMMAND}
    -DMODULE=$<TARGET_FILE:module_consumer> -DHEADER=$<TARGET_FILE:header_consumer>
    -DINPUT=${WWL_CODES_INPUT} -DREFERENCE=${WWL_REPORT_REFERENCE}
    -P ${CMAKE_CURRENT_SOURCE_DIR}/compare.cmake)
endif()
# This example does not install or redistribute compiler-specific BMI files.
