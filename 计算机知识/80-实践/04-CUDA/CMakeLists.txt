cmake_minimum_required(VERSION 3.24)

project(cuda_labs LANGUAGES CXX CUDA)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CUDA_STANDARD 17)
set(CMAKE_CUDA_STANDARD_REQUIRED ON)

if(NOT DEFINED CMAKE_CUDA_ARCHITECTURES OR CMAKE_CUDA_ARCHITECTURES STREQUAL "")
  message(FATAL_ERROR
    "Set CMAKE_CUDA_ARCHITECTURES to the reviewed target compute capability; use native only when the build GPU is visible and is the deployment target.")
endif()

include(CTest)

function(add_cuda_lab target)
  add_executable(${target} ${target}.cu)
  set_target_properties(${target} PROPERTIES
    CUDA_SEPARABLE_COMPILATION ON)
  target_compile_options(${target} PRIVATE
    $<$<COMPILE_LANGUAGE:CUDA>:--expt-relaxed-constexpr>)
  if(BUILD_TESTING)
    add_test(NAME ${target} COMMAND ${target})
    # 77 means the executable found no usable CUDA device; that is an
    # environment skip, not a failed correctness assertion.
    set_tests_properties(${target} PROPERTIES SKIP_RETURN_CODE 77)
  endif()
endfunction()

add_cuda_lab(01_vector_add)
add_cuda_lab(02_reduction)
add_cuda_lab(03_stable_softmax)
add_cuda_lab(03_tiled_gemm)
add_cuda_lab(04_profile_offload)
