# YOLO26 Profile Job — cluster attempt 1

Date: 2026-07-24  
Context: `profile-job-builder@k3s`  
Namespace: `profiling`  
Job: `yolo26-train-profile`  
Pod: `yolo26-train-profile-ft5mb`  
Node: `gx10-c206`

## Result

- Builder CLI server-side dry-run: passed
- Builder CLI `run`: Job created
- Pod scheduled to `gx10-c206`
- Requested resource: `nvidia.com/gpu.shared: "1"`
- Application profiler exit code: `1`
- Collector exit code: `0`
- Job result: `Failed` (`BackoffLimitExceeded`)
- Local artifact collection: passed

Application failure:

```text
ValueError: Invalid CUDA 'device=0' requested.
torch.cuda.is_available(): False
torch.cuda.device_count(): 0
os.environ['CUDA_VISIBLE_DEVICES']: None
```

Despite the application failure, Nsight Systems generated and the collector
parsed a valid failure-path report:

```text
profile.nsys-rep 362802 bytes
SHA-256 cf542e7837b4d290aec6536fdd33f7fdc5ec85d2fc3568ae2b6b109f623f36f7
nsys-stats.txt 6259 bytes
nsys-stats.csv 3735 bytes
```

Artifacts:

`artifacts/yolo26-train-profile/`

## Conclusion

Persistence, failure-path report generation, stats parsing, metadata enrichment,
collection acknowledgement, `kubectl cp`, and collector termination all worked.
The successful CPU–GPU workload criterion did not pass because the application
container did not see a CUDA device. The next diagnostic is a minimal
shared-GPU visibility Job using the node's `nvidia` RuntimeClass.
