#include <cuda_runtime.h>

#include <cstdio>

namespace {

constexpr int kElementCount = 1 << 20;
constexpr int kThreadsPerBlock = 256;

__global__ void increment(float* values, int count) {
  const int index = blockIdx.x * blockDim.x + threadIdx.x;
  if (index < count) {
    values[index] += 1.0F;
  }
}

bool check(cudaError_t result, const char* operation) {
  if (result == cudaSuccess) {
    return true;
  }
  std::fprintf(stderr, "%s failed: %s\n", operation, cudaGetErrorString(result));
  return false;
}

}  // namespace

int main() {
  float* values = nullptr;
  const std::size_t bytes = kElementCount * sizeof(float);

  if (!check(cudaMalloc(&values, bytes), "cudaMalloc")) {
    return 1;
  }
  if (!check(cudaMemset(values, 0, bytes), "cudaMemset")) {
    cudaFree(values);
    return 1;
  }

  const int blocks = (kElementCount + kThreadsPerBlock - 1) / kThreadsPerBlock;
  increment<<<blocks, kThreadsPerBlock>>>(values, kElementCount);

  if (!check(cudaGetLastError(), "kernel launch") ||
      !check(cudaDeviceSynchronize(), "cudaDeviceSynchronize")) {
    cudaFree(values);
    return 1;
  }
  if (!check(cudaFree(values), "cudaFree")) {
    return 1;
  }

  std::puts("CUDA smoke test completed");
  return 0;
}
