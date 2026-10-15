#include <cuda_runtime.h>

#include <cmath>
#include <cstdlib>
#include <iostream>
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

__global__ void vector_add(const float* a, const float* b, float* out, int n) {
  const int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i < n) out[i] = a[i] + b[i];
}

std::vector<float> vector_add_cpu(const std::vector<float>& a,
                                  const std::vector<float>& b) {
  std::vector<float> out(a.size());
  for (size_t i = 0; i < a.size(); ++i) out[i] = a[i] + b[i];
  return out;
}

int main() {
  int device_count = 0;
  const cudaError_t availability = cudaGetDeviceCount(&device_count);
  if (availability != cudaSuccess || device_count == 0) {
    std::cout << "SKIP: no usable CUDA device\n";
    cudaGetLastError();
    return 77;
  }

  constexpr int n = 1 << 20;
  std::vector<float> a(n), b(n);
  for (int i = 0; i < n; ++i) {
    a[i] = static_cast<float>(i) * 0.25F;
    b[i] = -static_cast<float>(i % 31) * 0.5F;
  }
  const auto expected = vector_add_cpu(a, b);

  float *d_a = nullptr, *d_b = nullptr, *d_out = nullptr;
  CUDA_CHECK(cudaMalloc(&d_a, n * sizeof(float)));
  CUDA_CHECK(cudaMalloc(&d_b, n * sizeof(float)));
  CUDA_CHECK(cudaMalloc(&d_out, n * sizeof(float)));
  CUDA_CHECK(cudaMemcpy(d_a, a.data(), n * sizeof(float), cudaMemcpyHostToDevice));
  CUDA_CHECK(cudaMemcpy(d_b, b.data(), n * sizeof(float), cudaMemcpyHostToDevice));

  constexpr int threads = 256;
  vector_add<<<(n + threads - 1) / threads, threads>>>(d_a, d_b, d_out, n);
  CUDA_CHECK(cudaGetLastError());
  CUDA_CHECK(cudaDeviceSynchronize());

  std::vector<float> actual(n);
  CUDA_CHECK(cudaMemcpy(actual.data(), d_out, n * sizeof(float), cudaMemcpyDeviceToHost));
  CUDA_CHECK(cudaFree(d_a));
  CUDA_CHECK(cudaFree(d_b));
  CUDA_CHECK(cudaFree(d_out));

  for (int i = 0; i < n; ++i) {
    if (!std::isfinite(actual[i]) || !std::isfinite(expected[i]) ||
        std::fabs(actual[i] - expected[i]) > 1e-6F) {
      std::cerr << "FAIL at " << i << ": got " << actual[i]
                << ", expected " << expected[i] << '\n';
      return EXIT_FAILURE;
    }
  }
  std::cout << "PASS: vector_add " << n << " elements\n";
}
