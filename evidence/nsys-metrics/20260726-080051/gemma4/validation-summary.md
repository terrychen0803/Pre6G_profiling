# Gemma 4 Nsight metrics rerun validation

- Job: `gemma4-nsys-metrics-20260726-080051`
- Node: `gx10-c206`
- Nsight Systems: `2025.3.2.474-253236389321v0`
- Workload status: success
- Application profiler exit code: `0`
- Collector exit code: `0`
- Report: `artifacts/profile.nsys-rep`
- Report size: `70,410,258` bytes
- Report SHA-256: `3c1778ad7a69d9e90d14fa7b965995d7c22357ab07d36aa36de8c4c864f6b597`
- SQLite export size: `1,167,818,752` bytes
- Collector checksum and local checksum: match

## Requested feature validation

| Feature | Result | Evidence |
| --- | --- | --- |
| CUDA trace | Collected | 184,909 CUDA runtime, 86,482 kernel, 3,689 memcpy, and 3,441 synchronization rows |
| NVTX trace | Collected | 419,839 NVTX rows |
| cuBLAS trace | Limited data | `cublasCreate_v2` event and cuBLAS-related symbols/kernels are present; no dedicated cuBLAS table was exported |
| cuDNN trace | Unsupported for loaded library | Nsight 2025.3.2 reports that cuDNN 9.2 tracing is unsupported and generated no cuDNN events |
| GPU metrics | Collected | 24,883,616 metric rows across 19 GB20B General Metrics |
| CPU sampling | Collected | 92,457 process-tree CPU sample events; Dwarf backtraces recorded |
| CPU context switches | Collected | 814,996 scheduler events |
| OS Runtime trace | Collected | 1,254,117 OSRT API rows |
| PyTorch functions and shapes | Collected | PyTorch autograd NVTX and Python Functions Trace initialized; operator names and tensor sizes are present |
| CUDA memory usage | Collected | 4,613 CUDA GPU memory usage events |
| File access | Collected | OSRT contains file operations including 22,975 `read`, 31,974 `write`, 12,526 `open64`, and 11,442 `close` calls |
| CPU core metrics | Unavailable | Nsight Systems 2025.3.2 on this target rejects both `--cpu-metrics=help` and `--cpu-core-metrics=help` |

## GPU metric set

Nsight selected `General Metrics for NVIDIA GB20B`. It includes clocks, copy
engines, graphics activity, SM activity, SM issue, Tensor activity, and compute
warps. This 19-metric set does not expose a separately named DRAM throughput
counter.

## Limitations

- GPU resource mode was `nvidia.com/gpu.shared`.
- An existing `gb10-yolo26-inference` Pod remained running on the same GB10.
  `--gpu-metrics-devices=all` is system-scope, so GPU metric samples may include
  activity from that existing workload.
- `SYS_ADMIN` was added only to this run's `trainer` container. The Pod was not
  privileged, `allowPrivilegeEscalation` remained false, and the collector
  continued to drop all capabilities.
- The host driver and kernel configuration were not modified.
