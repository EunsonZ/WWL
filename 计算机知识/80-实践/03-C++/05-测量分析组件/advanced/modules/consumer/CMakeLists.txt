# Separate consumer target: no private implementation include directories.
add_executable(module_consumer ../importer.cpp)
target_link_libraries(module_consumer PRIVATE measurement_module)
add_executable(header_consumer ../header_consumer.cpp)
target_link_libraries(header_consumer PRIVATE WWL::measurement)
foreach(target module_consumer header_consumer)
  target_compile_features(${target} PRIVATE cxx_std_20)
  set_target_properties(${target} PROPERTIES CXX_EXTENSIONS OFF)
  if(NOT MSVC)
    target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic
      -fno-fast-math -ffp-contract=off)
  endif()
endforeach()
