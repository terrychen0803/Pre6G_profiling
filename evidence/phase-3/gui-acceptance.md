# Phase 3 Nsight Systems GUI acceptance

Status: PASS with non-blocking limitations  
Prepared: 2026-07-24  
Accepted: 2026-07-25

## Report under review

- Profile Job: `yolo26-train-profile-phase4-run2`
- Workload: YOLO26n synthetic training, 2 epochs
- Node/GPU: `gx10-c206` / NVIDIA GB10 shared allocation
- Nsight Systems: 2025.3.2
- Report:
  `artifacts/yolo26-train-profile-phase4-run2/profile.nsys-rep`
- Size: 4,249,649 bytes
- SHA-256:
  `06ad732795c40fea5f2081b4adba1bba01076113cd933e3092a535d1b554d781`

CLI validation already passed:

- OS Runtime Summary
- CUDA API Summary
- CUDA GPU Kernel Summary
- CUDA GPU MemOps Summary by time
- CUDA GPU MemOps Summary by size
- producer/collector/local checksum equality

## GUI acceptance checklist

- [x] Report opens without corrupted-data warning
- [x] No incompatible-version error (`NewerReportVersionException` absent)
- [x] Session and Statistics pages open
- [x] Process and thread information is available for primary workload PID 96
- [x] CUDA trace is present: 163,464 events
- [x] NVTX trace is present: 439 events for primary workload PID 96
- [x] OS Runtime trace is present: 53,030 events for primary workload PID 96
- [x] CUDA injection initialized successfully
- [x] CUPTI trace is present: 169,663 events in 50 buffers
- [x] NVIDIA GB10 is identified: 48 SM, 119.61 GiB
- [x] Primary application process exited with code 0
- [x] Profiling session stopped cleanly after 12.953 seconds
- [x] CLI validation confirms CUDA API, GPU kernel and GPU memory-operation
  summaries

Application-level epoch/forward/backward/optimizer NVTX ranges are not required
because the frozen scope forbids application source modification.

## Recorded GUI evidence

The reviewed Session/System Summary established that the report imports into the
matching Nsight Systems 2025.3.2 GUI and contains usable CUDA, NVTX, OS Runtime,
CUPTI, process and GPU data.

The supplied screenshots are not currently stored in this repository. For a
stronger visual audit trail, the following additional files are recommended but
are not blockers for this acceptance:

1. `evidence/phase-3/gui/01-overall-timeline.png`
2. `evidence/phase-3/gui/02-cuda-api-kernel-correlation.png`
3. `evidence/phase-3/gui/03-gpu-memory-operations.png`
4. `evidence/phase-3/gui/04-session-system-summary.png`
5. `evidence/phase-3/gui/05-messages-and-limitations.png`

In particular, the first two would preserve direct visual evidence of the
CUDA API-to-GPU-kernel time relationship. The structured CLI summaries already
verify that GPU kernels and memory operations exist in the report.

## Session facts

- GUI / report version: Nsight Systems 2025.3.2
- Profiling duration: 12.953 seconds
- Report size shown by GUI: 4.05 MiB
- Total events collected: 223,424
- Primary workload: PID 96, 45 threads
- CUDA events: 163,464
- NVTX events: 439
- OS Runtime events: 53,030
- CUPTI events: 169,663 in 50 buffers
- GPU: NVIDIA GB10
- Driver: 580.159.03
- Application exit code: 0

## Non-blocking limitations

- Unified Memory tracing is unsupported by the current driver or configuration.
  It is outside the frozen `cuda,nvtx,osrt` trace scope and does not invalidate
  CUDA API, kernel or memory-operation tracing.
- CPU scheduling data was not collected. GUI CPU utilization is inferred from OS
  Runtime traces and must not be treated as benchmark-accurate utilization.
- PID 117 produced no CUDA or NVTX events. It was an auxiliary non-CUDA process;
  the primary workload PID 96 produced CUDA, NVTX and OS Runtime traces.
- The reviewed screenshots emphasize Session/System Summary. Dedicated overall
  timeline and CUDA API/kernel-correlation screenshots remain recommended.

## Reviewer record

- Reviewer: user-provided human GUI review
- GUI version: 2025.3.2
- Review recorded: 2026-07-25
- Overall result: PASS with non-blocking limitations

The `.nsys-rep` passed both structured CLI parsing and human GUI import and
inspection. It is suitable for subsequent engineering analysis within the
frozen scope.
