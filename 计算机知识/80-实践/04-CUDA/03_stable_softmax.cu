#include <cuda_runtime.h>

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <vector>

#define CUDA_CHECK(call)                                                        \
  do {                                                                          \
    const cudaError_t status = (call);                                          \
    if (status != cudaSuccess) {                                                \
      std::cerr << #call << " failed: " << cudaGetErrorString(status)          \
                << '\n';                                                       \
      std::exit(EXIT_FAILURE);                                                  \
    }                                                                           \
  } while (0)

__global__ void stable_softmax(const float* in, float* out, int n) {
  extern __shared__ float cache[];
  const int tid = threadIdx.x;
  cache[tid] = tid < n ? in[tid] : -INFINITY;
  __syncthreads();
  for (int stride = blockDim.x / 2; stride > 0; stride >>= 1) {
    if (tid < stride) cache[tid] = fmaxf(cache[tid], cache[tid + stride]);
    __syncthreads();
  }
  const float maximum = cache[0];
  const float value = tid < n ? expf(in[tid] - maximum) : 0.0F;
  cache[tid] = value;
  __syncthreads();
  for (int stride = blockDim.x / 2; stride > 0; stride >>= 1) {
    if (tid < stride) cache[tid] += cache[tid + stride];
    __syncthreads();
  }
  if (tid < n) out[tid] = value / cache[0];
}

std::vector<float> stable_softmax_cpu(const std::vector<float>& input) {
  const float maximum = *std::max_element(input.begin(), input.end());
  std::vector<float> output(input.size());
  float denominator = 0.0F;
  for (size_t i = 0; i < input.size(); ++i) {
    output[i] = std::exp(input[i] - maximum);
    denominator += output[i];
  }
  for (float& value : output) value /= denominator;
  return output;
}

int main() {
  int device_count = 0;
  const cudaError_t availability = cudaGetDeviceCount(&device_count);
  if (availability != cudaSuccess || device_count == 0) {
    std::cout << "SKIP: no usable CUDA device\n";
    cudaGetLastError();
    return 77;
  }

  constexpr int n = 256;
  std::vector<float> input(n);
  for (int i = 0; i < n; ++i) input[i] = -80.0F + static_cast<float>(i) * 0.625F;
  const auto expected = stable_softmax_cpu(input);

  float *d_input = nullptr, *d_output = nullptr;
  CUDA_CHECK(cudaMalloc(&d_input, n * sizeof(float)));
  CUDA_CHECK(cudaMalloc(&d_output, n * sizeof(float)));
  CUDA_CHECK(cudaMemcpy(d_input, input.data(), n * sizeof(float), cudaMemcpyHostToDevice));
  stable_softmax<<<1, 256, 256 * sizeof(float)>>>(d_input, d_output, n);
  CUDA_CHECK(cudaGetLastError());
  CUDA_CHECK(cudaDeviceSynchronize());

  std::vector<float> actual(n);
  CUDA_CHECK(cudaMemcpy(actual.data(), d_output, n * sizeof(float), cudaMemcpyDeviceToHost));
  CUDA_CHECK(cudaFree(d_input));
  CUDA_CHECK(cudaFree(d_output));

  const float sum = std::accumulate(actual.begin(), actual.end(), 0.0F);
  for (int i = 0; i < n; ++i) {
    if (!std::isfinite(actual[i]) || std::fabs(actual[i] - expected[i]) > 2e-5F) {
      std::cerr << "FAIL at " << i << ": got " << actual[i]
                << ", expected " << expected[i] << '\n';
      return EXIT_FAILURE;
    }
  }
  if (std::fabs(sum - 1.0F) > 1e-5F) {
    std::cerr << "FAIL: softmax sum is " << sum << '\n';
    return EXIT_FAILURE;
  }
  std::cout << "PASS: stable softmax; sum=" << sum << '\n';
}
