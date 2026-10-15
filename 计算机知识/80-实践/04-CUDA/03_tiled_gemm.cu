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

constexpr int tile_size = 16;

__global__ void tiled_gemm(const float* a, const float* b, float* c,
                           int m, int n, int k) {
  __shared__ float a_tile[tile_size][tile_size];
  __shared__ float b_tile[tile_size][tile_size];

  const int row = blockIdx.y * tile_size + threadIdx.y;
  const int col = blockIdx.x * tile_size + threadIdx.x;
  float accumulator = 0.0F;

  for (int tile = 0; tile < (k + tile_size - 1) / tile_size; ++tile) {
    const int a_col = tile * tile_size + threadIdx.x;
    const int b_row = tile * tile_size + threadIdx.y;
    a_tile[threadIdx.y][threadIdx.x] =
        (row < m && a_col < k) ? a[row * k + a_col] : 0.0F;
    b_tile[threadIdx.y][threadIdx.x] =
        (b_row < k && col < n) ? b[b_row * n + col] : 0.0F;
    __syncthreads();

#pragma unroll
    for (int inner = 0; inner < tile_size; ++inner) {
      accumulator += a_tile[threadIdx.y][inner] *
                     b_tile[inner][threadIdx.x];
    }
    __syncthreads();
  }

  if (row < m && col < n) {
    c[row * n + col] = accumulator;
  }
}

std::vector<float> gemm_cpu(const std::vector<float>& a,
                            const std::vector<float>& b,
                            int m, int n, int k) {
  std::vector<float> c(static_cast<std::size_t>(m) * n, 0.0F);
  for (int row = 0; row < m; ++row) {
    for (int col = 0; col < n; ++col) {
      float accumulator = 0.0F;
      for (int inner = 0; inner < k; ++inner) {
        accumulator += a[row * k + inner] * b[inner * n + col];
      }
      c[row * n + col] = accumulator;
    }
  }
  return c;
}

int main() {
  int device_count = 0;
  const cudaError_t availability = cudaGetDeviceCount(&device_count);
  if (availability != cudaSuccess || device_count == 0) {
    std::cout << "SKIP: no usable CUDA device\n";
    cudaGetLastError();
    return 77;
  }

  // Deliberately not multiples of tile_size: this exercises all edge guards.
  constexpr int m = 65;
  constexpr int n = 67;
  constexpr int k = 33;
  std::vector<float> a(static_cast<std::size_t>(m) * k);
  std::vector<float> b(static_cast<std::size_t>(k) * n);
  for (std::size_t i = 0; i < a.size(); ++i) {
    a[i] = static_cast<float>(static_cast<int>(i % 17) - 8) * 0.125F;
  }
  for (std::size_t i = 0; i < b.size(); ++i) {
    b[i] = static_cast<float>(static_cast<int>(i % 11) - 5) * 0.0625F;
  }
  const auto expected = gemm_cpu(a, b, m, n, k);
  std::vector<float> actual(static_cast<std::size_t>(m) * n, 0.0F);

  float *d_a = nullptr, *d_b = nullptr, *d_c = nullptr;
  CUDA_CHECK(cudaMalloc(&d_a, a.size() * sizeof(float)));
  CUDA_CHECK(cudaMalloc(&d_b, b.size() * sizeof(float)));
  CUDA_CHECK(cudaMalloc(&d_c, actual.size() * sizeof(float)));
  CUDA_CHECK(cudaMemcpy(d_a, a.data(), a.size() * sizeof(float),
                        cudaMemcpyHostToDevice));
  CUDA_CHECK(cudaMemcpy(d_b, b.data(), b.size() * sizeof(float),
                        cudaMemcpyHostToDevice));

  const dim3 block(tile_size, tile_size);
  const dim3 grid((n + tile_size - 1) / tile_size,
                  (m + tile_size - 1) / tile_size);
  tiled_gemm<<<grid, block>>>(d_a, d_b, d_c, m, n, k);
  CUDA_CHECK(cudaGetLastError());
  CUDA_CHECK(cudaDeviceSynchronize());
  CUDA_CHECK(cudaMemcpy(actual.data(), d_c, actual.size() * sizeof(float),
                        cudaMemcpyDeviceToHost));

  CUDA_CHECK(cudaFree(d_c));
  CUDA_CHECK(cudaFree(d_b));
  CUDA_CHECK(cudaFree(d_a));

  float max_abs_error = 0.0F;
  for (std::size_t i = 0; i < actual.size(); ++i) {
    if (!std::isfinite(actual[i])) {
      std::cerr << "FAIL: non-finite GEMM result at " << i << '\n';
      return EXIT_FAILURE;
    }
    max_abs_error =
        std::fmax(max_abs_error, std::fabs(actual[i] - expected[i]));
  }
  if (max_abs_error > 1e-4F) {
    std::cerr << "FAIL: max absolute error " << max_abs_error << '\n';
    return EXIT_FAILURE;
  }
  std::cout << "PASS: tiled GEMM " << m << 'x' << k << " @ " << k << 'x'
            << n << ", max-abs-error=" << max_abs_error << '\n';
}
