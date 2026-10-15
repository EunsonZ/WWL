#include <cuda_runtime.h>

#include <cmath>
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <utility>
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

__global__ void reduce_sum(const float* in, float* partial, int n) {
  extern __shared__ float cache[];
  const unsigned int tid = threadIdx.x;
  const unsigned int i = blockIdx.x * (blockDim.x * 2) + tid;
  float value = 0.0F;
  if (i < static_cast<unsigned int>(n)) value += in[i];
  if (i + blockDim.x < static_cast<unsigned int>(n)) value += in[i + blockDim.x];
  cache[tid] = value;
  __syncthreads();
  for (unsigned int stride = blockDim.x / 2; stride > 0; stride >>= 1) {
    if (tid < stride) cache[tid] += cache[tid + stride];
    __syncthreads();
  }
  if (tid == 0) partial[blockIdx.x] = cache[0];
}

// Adjacent threads read adjacent elements when stride is 1.  Raising stride
// demonstrates a less coalesced access pattern without changing correctness.
__global__ void strided_read(const float* in, float* out, int n, int stride) {
  const int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i < n) out[i] = in[(i * stride) % n];
}

float sum_cpu(const std::vector<float>& values) {
  return std::accumulate(values.begin(), values.end(), 0.0F);
}

int main() {
  int device_count = 0;
  const cudaError_t availability = cudaGetDeviceCount(&device_count);
  if (availability != cudaSuccess || device_count == 0) {
    std::cout << "SKIP: no usable CUDA device\n";
    cudaGetLastError();
    return 77;
  }

  constexpr int n = (1 << 20) + 37;
  constexpr int threads = 256;
  std::vector<float> host(n);
  for (int i = 0; i < n; ++i) host[i] = static_cast<float>((i % 13) - 6) * 0.125F;
  const float expected = sum_cpu(host);

  float *d_current = nullptr, *d_next = nullptr, *d_probe = nullptr;
  CUDA_CHECK(cudaMalloc(&d_current, n * sizeof(float)));
  CUDA_CHECK(cudaMalloc(&d_next, n * sizeof(float)));
  CUDA_CHECK(cudaMalloc(&d_probe, n * sizeof(float)));
  CUDA_CHECK(cudaMemcpy(d_current, host.data(), n * sizeof(float), cudaMemcpyHostToDevice));
  CUDA_CHECK(cudaMemcpy(d_probe, host.data(), n * sizeof(float), cudaMemcpyHostToDevice));

  // This is a correctness-first multi-stage reduction, not a vendor-tuned kernel.
  int current_n = n;
  while (current_n > 1) {
    const int blocks = (current_n + threads * 2 - 1) / (threads * 2);
    reduce_sum<<<blocks, threads, threads * sizeof(float)>>>(d_current, d_next, current_n);
    CUDA_CHECK(cudaGetLastError());
    std::swap(d_current, d_next);
    current_n = blocks;
  }
  float actual = 0.0F;
  CUDA_CHECK(cudaMemcpy(&actual, d_current, sizeof(float), cudaMemcpyDeviceToHost));

  // Keep this launch in the experiment: profile stride 1 and 32 separately.
  strided_read<<<(n + threads - 1) / threads, threads>>>(d_probe, d_next, n, 1);
  CUDA_CHECK(cudaGetLastError());
  CUDA_CHECK(cudaDeviceSynchronize());
  CUDA_CHECK(cudaFree(d_current));
  CUDA_CHECK(cudaFree(d_next));
  CUDA_CHECK(cudaFree(d_probe));

  if (!std::isfinite(actual) || !std::isfinite(expected) ||
      std::fabs(actual - expected) > 1e-2F) {
    std::cerr << "FAIL: got " << actual << ", expected " << expected << '\n';
    return EXIT_FAILURE;
  }
  std::cout << "PASS: reduction result " << actual << '\n';
}
