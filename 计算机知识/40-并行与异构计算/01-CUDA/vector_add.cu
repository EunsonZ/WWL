#include <cuda_runtime.h>

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

__global__ void vector_add(const float* a, const float* b, float* c, int n) {
  const int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i < n) {
    c[i] = a[i] + b[i];
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


  constexpr int n = 1000;
  const std::size_t bytes = n * sizeof(float);
  std::vector<float> a(n, 1.5F);
  std::vector<float> b(n, 2.0F);
  std::vector<float> c(n, 0.0F);

  float* d_a = nullptr;
  float* d_b = nullptr;
  float* d_c = nullptr;
  CUDA_CHECK(cudaMalloc(&d_a, bytes));
  CUDA_CHECK(cudaMalloc(&d_b, bytes));
  CUDA_CHECK(cudaMalloc(&d_c, bytes));
  CUDA_CHECK(cudaMemcpy(d_a, a.data(), bytes, cudaMemcpyHostToDevice));
  CUDA_CHECK(cudaMemcpy(d_b, b.data(), bytes, cudaMemcpyHostToDevice));

  constexpr int threads = 256;
  const int blocks = (n + threads - 1) / threads;
  vector_add<<<blocks, threads>>>(d_a, d_b, d_c, n);
  CUDA_CHECK(cudaGetLastError());
  CUDA_CHECK(cudaMemcpy(c.data(), d_c, bytes, cudaMemcpyDeviceToHost));

  for (int i = 0; i < n; ++i) {
    if (std::fabs(c[i] - 3.5F) > 1e-6F) {
      std::fprintf(stderr, "Mismatch at %d: %f\n", i, c[i]);
      cudaFree(d_c);
      cudaFree(d_b);
      cudaFree(d_a);
      return 1;
    }
  }

  CUDA_CHECK(cudaFree(d_c));
  CUDA_CHECK(cudaFree(d_b));
  CUDA_CHECK(cudaFree(d_a));
  std::puts("PASS: vector_add");
  return 0;
}
