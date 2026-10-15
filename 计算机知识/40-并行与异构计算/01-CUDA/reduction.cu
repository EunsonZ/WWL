#include <cuda_runtime.h>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <vector>

#define CUDA_CHECK(call)                                                     \
  do {                                                                       \
    const cudaError_t error = (call);                                        \
    if (error != cudaSuccess) {                                              \
      std::fprintf(stderr, "CUDA error at %s:%d: %s\n", __FILE__, __LINE__, \
                   cudaGetErrorString(error));                               \
      return 1;                                                              \
    }                                                                        \
  } while (0)

template <int block_size>
__global__ void reduce_sum(const float* input, float* partial, int n) {
  __shared__ float tile[block_size];
  const int lane = threadIdx.x;
  const int first = blockIdx.x * (2 * block_size) + lane;

  float local = 0.0F;
  if (first < n) {
    local += input[first];
  }
  const int second = first + block_size;
  if (second < n) {
    local += input[second];
  }
  tile[lane] = local;
  __syncthreads();

  for (int stride = block_size / 2; stride > 0; stride /= 2) {
    if (lane < stride) {
      tile[lane] += tile[lane + stride];
    }
    __syncthreads();
  }

  if (lane == 0) {
    partial[blockIdx.x] = tile[0];
  }
}

int main() {
  int device_count = 0;
  const cudaError_t availability = cudaGetDeviceCount(&device_count);
  if (availability != cudaSuccess || device_count == 0) {
    std::puts("SKIP: no usable CUDA device");
    cudaGetLastError();
    return 77;
  }


  constexpr int n = (1 << 20) + 3;
  constexpr int threads = 256;
  const int blocks = (n + 2 * threads - 1) / (2 * threads);

  std::vector<float> input(n);
  double expected = 0.0;
  for (int i = 0; i < n; ++i) {
    input[i] = static_cast<float>((i % 13) - 6);
    expected += input[i];
  }
  std::vector<float> partial(blocks, 0.0F);

  float* d_input = nullptr;
  float* d_partial = nullptr;
  CUDA_CHECK(cudaMalloc(&d_input, n * sizeof(float)));
  CUDA_CHECK(cudaMalloc(&d_partial, blocks * sizeof(float)));
  CUDA_CHECK(cudaMemcpy(d_input, input.data(), n * sizeof(float),
                        cudaMemcpyHostToDevice));

  reduce_sum<threads><<<blocks, threads>>>(d_input, d_partial, n);
  CUDA_CHECK(cudaGetLastError());
  CUDA_CHECK(cudaMemcpy(partial.data(), d_partial, blocks * sizeof(float),
                        cudaMemcpyDeviceToHost));

  double result = 0.0;
  for (const float value : partial) {
    result += value;
  }

  CUDA_CHECK(cudaFree(d_partial));
  CUDA_CHECK(cudaFree(d_input));
  if (!std::isfinite(result) || !std::isfinite(expected) ||
      std::fabs(result - expected) > 1e-6) {
    std::fprintf(stderr, "Mismatch: got %.9f expected %.9f\n", result,
                 expected);
    return 1;
  }
  std::printf("PASS: reduction result %.1f from %d block partials\n", result,
              blocks);
  return 0;
}
