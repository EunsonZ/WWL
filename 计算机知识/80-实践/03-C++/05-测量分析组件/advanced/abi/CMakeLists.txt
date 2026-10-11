cmake_minimum_required(VERSION 3.20)
project(WWLMeasurementABI VERSION 1.0.0 LANGUAGES CXX)
include(CTest)
include(GNUInstallDirs)
include(CMakePackageConfigHelpers)
find_package(WWLMeasurement 1.2 CONFIG REQUIRED)
add_library(measurement_abi SHARED measurement_abi.cpp)
add_library(WWL::measurement_abi ALIAS measurement_abi)
target_compile_features(measurement_abi PRIVATE cxx_std_20)
target_compile_definitions(measurement_abi PRIVATE WWL_ABI_BUILD)
target_include_directories(measurement_abi PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>)
target_link_libraries(measurement_abi PRIVATE WWL::measurement)
set_target_properties(measurement_abi PROPERTIES VERSION 1.0.0 SOVERSION 1
  CXX_EXTENSIONS OFF CXX_VISIBILITY_PRESET hidden VISIBILITY_INLINES_HIDDEN YES)
# The installed static base is internal to this dylib. Restrict the exports of
# both wrapper and archive objects; visibility flags alone cannot hide an archive
# that was previously built with default visibility.
set(abi_exports wwl_report_create_v1 wwl_report_destroy_v1 wwl_report_replace_v1
  wwl_report_copy_text_v1 wwl_report_get_layout_v1)
if(APPLE)
  foreach(symbol IN LISTS abi_exports)
    target_link_options(measurement_abi PRIVATE "LINKER:-exported_symbol,_${symbol}")
  endforeach()
elseif(UNIX)
  file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/abi.exports" "{ global: wwl_report_*_v1; local: *; };\n")
  target_link_options(measurement_abi PRIVATE
    "LINKER:--version-script=${CMAKE_CURRENT_BINARY_DIR}/abi.exports")
endif()
function(abi_options target)
  if(MSVC)
    target_compile_options(${target} PRIVATE /W4 /permissive- /fp:strict)
  else()
    target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic -fno-fast-math -ffp-contract=off)
  endif()
endfunction()
abi_options(measurement_abi)
if(BUILD_TESTING)
  # Separate uninstalled implementation variant. No testing hooks in the dylib.
  add_executable(abi_tests tests.cpp measurement_abi.cpp)
  target_compile_features(abi_tests PRIVATE cxx_std_20)
  target_compile_definitions(abi_tests PRIVATE WWL_ABI_BUILD WWL_ABI_TESTING)
  target_include_directories(abi_tests PRIVATE include)
  target_link_libraries(abi_tests PRIVATE WWL::measurement)
  abi_options(abi_tests)
  add_test(NAME abi_failures_and_ownership COMMAND abi_tests)
  # This regression links the real SHARED implementation, not WWL_ABI_TESTING.
  add_executable(abi_default_resource_tests tests_default_resource.cpp)
  target_compile_features(abi_default_resource_tests PRIVATE cxx_std_20)
  target_link_libraries(abi_default_resource_tests PRIVATE WWL::measurement_abi)
  abi_options(abi_default_resource_tests)
  add_test(NAME abi_default_resource_lifetime COMMAND abi_default_resource_tests)
endif()
install(TARGETS measurement_abi EXPORT WWLMeasurementABITargets
  LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
  RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
  ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR})
install(DIRECTORY include/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
install(EXPORT WWLMeasurementABITargets NAMESPACE WWL::
  DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/WWLMeasurementABI)
configure_package_config_file(Config.cmake.in
  "${CMAKE_CURRENT_BINARY_DIR}/WWLMeasurementABIConfig.cmake"
  INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/WWLMeasurementABI)
write_basic_package_version_file("${CMAKE_CURRENT_BINARY_DIR}/WWLMeasurementABIConfigVersion.cmake"
  VERSION ${PROJECT_VERSION} COMPATIBILITY SameMajorVersion)
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/WWLMeasurementABIConfig.cmake"
  "${CMAKE_CURRENT_BINARY_DIR}/WWLMeasurementABIConfigVersion.cmake"
  DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/WWLMeasurementABI)
