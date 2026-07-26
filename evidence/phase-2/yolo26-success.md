# YOLO26 Profile Job — successful cluster run

Date: 2026-07-24  
Context: `profile-job-builder@k3s`  
Namespace: `profiling`  
Job: `yolo26-train-profile-run2`  
Pod: `yolo26-train-profile-run2-vpltq`  
Node: `gx10-c206`  
RuntimeClass: `nvidia`  
GPU resource: `nvidia.com/gpu.shared: "1"`

## Application

- Image: `ultralytics/ultralytics:8.4.104-nvidia-arm64@sha256:7db35781a755d11717f67b085f71b9b2ddee6c491c958e76e2526597a85b4757`
- GPU: NVIDIA GB10
- Workload: YOLO26n synthetic dataset, 2 epochs
- Training: completed
- Application profiler exit code: `0`
- Collector exit code: `0`
- Kubernetes Job condition: `Complete`

## Artifacts

Local directory:

`artifacts/yolo26-train-profile-run2/`

```text
application.log       9594 bytes
nsys-stats.csv       79510 bytes
nsys-stats.txt       56768 bytes
pod.json             26458 bytes
profile-job.yaml      8035 bytes
profile-metadata.json 1187 bytes
profile.nsys-rep   4098639 bytes
profile.sqlite     11239424 bytes
```

Report SHA-256:

```text
265c8701c7da9cc2a83b393c728469ca95deb69d62ef95edb62a0db58bb757b0
```

`nsys stats` contains:

- OS Runtime Summary
- CUDA API Summary
- CUDA GPU Kernel Summary
- CUDA GPU MemOps Summary by time
- CUDA GPU MemOps Summary by size

## Result

The reference Kubernetes workload was independently wrapped by Nsight Systems
without application source changes, ran on a shared NVIDIA GB10 allocation,
produced a non-empty report, parsed the report, persisted it to the PVC, and
collected the artifact set to the management workspace.

After the Profile Job and Pod were deleted, a separate read-only Job mounted the
PVC and verified:

```text
4098639 profile.nsys-rep
56768 nsys-stats.txt
79510 nsys-stats.csv
265c8701c7da9cc2a83b393c728469ca95deb69d62ef95edb62a0db58bb757b0 profile.nsys-rep
yolo-artifact-persistence-ok
```
