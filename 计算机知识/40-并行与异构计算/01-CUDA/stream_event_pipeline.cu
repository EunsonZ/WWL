#include <cuda_runtime.h>

#include <cmath>
#include <cstdio>
#include <cstdlib>

#define CUDA_CHECK(call)                                                     \
  do {                                                                       \
    const cudaError_t error = (call);                                        \
    if (error != cudaSuccess) {                                              \
      std::fprintf(stderr, "CUDA error at %s:%d: %s\n", __FILE__, __LINE__, \
                   cudaGetErrorString(error));                               \
      std::exit(EXIT_FAILURE);                                               \
    }                                                                        \
  } while (0)

__global__ void add(const float* a, const float* b, float* c, int n) {
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


  constexpr int chunks = 2;
  constexpr int chunk_elements = 1 << 19;
  constexpr int total_elements = chunks * chunk_elements;
  constexpr std::size_t chunk_bytes = chunk_elements * sizeof(float);
  constexpr std::size_t total_bytes = total_elements * sizeof(float);

  float* h_a = nullptr;
  float* h_b = nullptr;
  float* h_c = nullptr;
  CUDA_CHECK(cudaMallocHost(&h_a, total_bytes));
  CUDA_CHECK(cudaMallocHost(&h_b, total_bytes));
  CUDA_CHECK(cudaMallocHost(&h_c, total_bytes));

  for (int i = 0; i < total_elements; ++i) {
    h_a[i] = static_cast<float>(i % 97);
    h_b[i] = 0.5F;
    h_c[i] = 0.0F;
  }

  cudaStream_t streams[chunks]{};
  cudaEvent_t done[chunks]{};
  float* d_a[chunks]{};
  float* d_b[chunks]{};
  float* d_c[chunks]{};

  constexpr int threads = 256;
  constexpr int blocks = (chunk_elements + threads - 1) / threads;

  for (int k = 0; k < chunks; ++k) {
    CUDA_CHECK(cudaStreamCreateWithFlags(&streams[k], cudaStreamNonBlocking));
    CUDA_CHECK(cudaEventCreateWithFlags(&done[k], cudaEventDisableTiming));
    CUDA_CHECK(cudaMalloc(&d_a[k], chunk_bytes));
    CUDA_CHECK(cudaMalloc(&d_b[k], chunk_bytes));
    CUDA_CHECK(cudaMalloc(&d_c[k], chunk_bytes));
  }

  // Traditional cudaMalloc may synchronize the device. Finish every stream,
  // event and allocation before enqueueing either chunk so allocation cannot
  // serialize the two candidate pipelines between their submissions.
  for (int k = 0; k < chunks; ++k) {
    const int offset = k * chunk_elements;
    CUDA_CHECK(cudaMemcpyAsync(d_a[k], h_a + offset, chunk_bytes,
                               cudaMemcpyHostToDevice, streams[k]));
    CUDA_CHECK(cudaMemcpyAsync(d_b[k], h_b + offset, chunk_bytes,
                               cudaMemcpyHostToDevice, streams[k]));
    add<<<blocks, threads, 0, streams[k]>>>(d_a[k], d_b[k], d_c[k],
                                           chunk_elements);
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaMemcpyAsync(h_c + offset, d_c[k], chunk_bytes,
                               cudaMemcpyDeviceToHost, streams[k]));
    CUDA_CHECK(cudaEventRecord(done[k], streams[k]));
  }

  for (int k = 0; k < chunks; ++k) {
    CUDA_CHECK(cudaEventSynchronize(done[k]));
  }

  for (int i = 0; i < total_elements; ++i) {
    const float expected = h_a[i] + h_b[i];
    if (!std::isfinite(h_c[i]) || !std::isfinite(expected) ||
        std::fabs(h_c[i] - expected) > 1e-6F) {
      std::fprintf(stderr, "Mismatch at %d: got %f expected %f\n", i, h_c[i],
                   expected);
      return 1;
    }
  }

  for (int k = 0; k < chunks; ++k) {
    CUDA_CHECK(cudaFree(d_c[k]));
    CUDA_CHECK(cudaFree(d_b[k]));
    CUDA_CHECK(cudaFree(d_a[k]));
    CUDA_CHECK(cudaEventDestroy(done[k]));
    CUDA_CHECK(cudaStreamDestroy(streams[k]));
  }
  CUDA_CHECK(cudaFreeHost(h_c));
  CUDA_CHECK(cudaFreeHost(h_b));
  CUDA_CHECK(cudaFreeHost(h_a));

  std::puts("PASS: two-stream pipeline");
  return 0;
}
