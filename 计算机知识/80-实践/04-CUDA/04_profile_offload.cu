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

__global__ void saxpy(float a, const float* x, float* y, int n) {
  const int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i < n) y[i] = a * x[i] + y[i];
}

void saxpy_cpu(float a, const std::vector<float>& x, std::vector<float>& y) {
  for (size_t i = 0; i < x.size(); ++i) y[i] = a * x[i] + y[i];
}

int main() {
  int device_count = 0;
  const cudaError_t availability = cudaGetDeviceCount(&device_count);
  if (availability != cudaSuccess || device_count == 0) {
    std::cout << "SKIP: no usable CUDA device\n";
    cudaGetLastError();
    return 77;
  }

  constexpr int n = 1 << 22;
  constexpr int threads = 256;
  constexpr int warmup = 10;
  constexpr int iterations = 100;
  std::vector<float> x(n, 1.5F), y(n, -2.0F), expected = y;
  for (int i = 0; i < warmup + iterations; ++i) saxpy_cpu(0.5F, x, expected);

  float *d_x = nullptr, *d_y = nullptr;
  CUDA_CHECK(cudaMalloc(&d_x, n * sizeof(float)));
  CUDA_CHECK(cudaMalloc(&d_y, n * sizeof(float)));
  CUDA_CHECK(cudaMemcpy(d_x, x.data(), n * sizeof(float), cudaMemcpyHostToDevice));
  CUDA_CHECK(cudaMemcpy(d_y, y.data(), n * sizeof(float), cudaMemcpyHostToDevice));
  for (int i = 0; i < warmup; ++i) saxpy<<<(n + threads - 1) / threads, threads>>>(0.5F, d_x, d_y, n);
  CUDA_CHECK(cudaGetLastError());
  CUDA_CHECK(cudaDeviceSynchronize());

  cudaEvent_t start, stop;
  CUDA_CHECK(cudaEventCreate(&start));
  CUDA_CHECK(cudaEventCreate(&stop));
  CUDA_CHECK(cudaEventRecord(start));
  for (int i = 0; i < iterations; ++i) saxpy<<<(n + threads - 1) / threads, threads>>>(0.5F, d_x, d_y, n);
  CUDA_CHECK(cudaEventRecord(stop));
  CUDA_CHECK(cudaEventSynchronize(stop));
  CUDA_CHECK(cudaGetLastError());
  float milliseconds = 0.0F;
  CUDA_CHECK(cudaEventElapsedTime(&milliseconds, start, stop));

  CUDA_CHECK(cudaMemcpy(y.data(), d_y, n * sizeof(float), cudaMemcpyDeviceToHost));
  CUDA_CHECK(cudaEventDestroy(start));
  CUDA_CHECK(cudaEventDestroy(stop));
  CUDA_CHECK(cudaFree(d_x));
  CUDA_CHECK(cudaFree(d_y));
  float max_abs_error = 0.0F;
  for (int i = 0; i < n; ++i) {
    if (!std::isfinite(y[i])) {
      std::cerr << "FAIL: non-finite SAXPY result at " << i << '\n';
      return EXIT_FAILURE;
    }
    max_abs_error = std::fmax(max_abs_error, std::fabs(y[i] - expected[i]));
  }
  if (max_abs_error > 1e-4F) {
    std::cerr << "FAIL: max absolute error " << max_abs_error << '\n';
    return EXIT_FAILURE;
  }
  std::cout << "PASS: " << iterations << " SAXPY launches, average "
            << milliseconds / iterations << " ms, max-abs-error="
            << max_abs_error << "\n";
}
