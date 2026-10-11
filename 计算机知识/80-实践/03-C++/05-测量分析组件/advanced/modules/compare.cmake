execute_process(COMMAND "${MODULE}" "${INPUT}" RESULT_VARIABLE module_exit
  OUTPUT_VARIABLE module_text ERROR_VARIABLE module_error)
execute_process(COMMAND "${HEADER}" "${INPUT}" RESULT_VARIABLE header_exit
  OUTPUT_VARIABLE header_text ERROR_VARIABLE header_error)
file(READ "${REFERENCE}" expected)
if(NOT module_exit EQUAL 0 OR NOT header_exit EQUAL 0)
  message(FATAL_ERROR "Consumer failed: module=${module_exit}, header=${header_exit}")
endif()
if(NOT module_text STREQUAL header_text OR NOT module_text STREQUAL expected)
  message(FATAL_ERROR "Header/module report differs from the published reference")
endif()
message(STATUS "Module/header/public-reference reports are byte-identical")
