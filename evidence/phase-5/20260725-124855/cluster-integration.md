# Phase 5 Kubernetes Integration Acceptance

## Overall result

**PASS — source-tree checksum bound**

All three Kubernetes paths and all seven CLI commands have reproducible command
transcripts, exit codes, final Job/Pod state, metadata checks, artifact checks
and independent clean verification.

The acceptance run is bound to the following source-tree SHA-256:

`a95b470d8bbf9cea779da7aa70aa8dab12efd6abfe679009c25502ae9628b40a`

The workspace was not a Git worktree at the time of acceptance. Git commit
traceability is deferred as a non-blocking release-engineering item and does
not invalidate the completed functional and Kubernetes integration evidence.

## Environment

- Timestamp: 2026-07-25T12:49:17+08:00
- Host: `gx10-c206`
- User: `good_egg`
- Kubernetes context: `profile-job-builder@k3s`
- Namespace: `profiling`
- Node: `gx10-c206` (`Ready`, k3s v1.35.4+k3s1)
- GPU resource: `nvidia.com/gpu.shared=4`; dedicated resource absent
- Python: 3.14.6
- Nsight Systems: 2025.3.2
- Offline tests: 45/45 passed, exit 0
- Git SHA: unavailable; workspace is not a Git worktree

All required RBAC checks returned `yes`: create/delete Job, read Pod/log, Pod
exec, and read Node.

## CLI contract

Help output for the root command and all seven subcommands is stored under
`environment/`.

| Command | Help captured | Success | App failure | Collector failure |
|---|---:|---:|---:|---:|
| `inspect` | PASS | 0 | 0 | 0 |
| `validate` | PASS | 0 | 0 | 0 |
| `build` | PASS | 0 | 0 | 0 |
| `diff` | PASS | 0 | 0 | 0 |
| `run` | PASS | 0 | 0 | 0 |
| `collect` | PASS | 0 | 2, expected | 2, expected |
| `clean` | PASS | 0 | 0 | 0 |

The collector intentionally waits for the Builder collection acknowledgement.
The implemented sequence is therefore `run → collect → Job terminal
condition`, rather than waiting for Job completion before `collect`.

## Path A — Success

- Job: `phase5-success-20260725-124855`
- Job condition: Complete
- Application exit: 0
- Collector exit: 0
- Overall status: `success`
- Report valid / stats complete: true / true
- Report: 4,134,386 bytes
- Report SHA-256:
  `3989d92cc3b1e615338f2303614b039e1b54fb18738eaeaa186d900a51fa096b`
- Producer, collector and local checksums: equal
- Six required artifacts: present and non-empty
- Clean exit: 0
- Post-clean Job: NotFound
- Post-clean Pods: 0
- Local artifacts after clean: retained

## Path B — Application exit 7

- Job: `phase5-appfail-20260725-124855`
- Workload completed YOLO CUDA training, emitted the marker, then exited 7
- Job condition: Failed; no false Complete condition
- Application exit: 7
- Collector exit: 27
- Builder `collect`: 2
- Overall status: `failed`
- Failure reason: `application_exit_nonzero`
- Report valid / stats complete: true / true
- Report: 4,134,249 bytes
- Report SHA-256:
  `7c6aeb01389e3f7d015977743e38f521c876e899c994aed9154d93eb140f7c33`
- Checksum equality: true
- Report, final stats, logs and metadata: retained
- Clean exit: 0; Job NotFound; post-clean Pods: 0

## Path C — Collector stats failure

- Job: `phase5-colfail-20260725-124855`
- Application exit: 0
- Collector exit: 26
- Builder `collect`: 2
- Job condition: Failed; no false Complete condition
- Overall status / failure reason: `failed` / `stats_failure`
- Report exists / checksum equality: true / true
- Stats complete: false
- Final `nsys-stats.txt` and CSV were not published
- Parser stderr and diagnostic artifacts: retained
- Clean exit: 0; Job NotFound; post-clean Pods: 0

The failure used the collector's existing `PROFILE_REQUIRED_REPORTS` test
control with `definitely_not_a_report`. The exact one-field manifest overlay,
before/after manifests and checksums are preserved in
`collector-failure/failure-injection.diff` and
`collector-failure/failure-injection.sha256`. The submitted Job was not mutated
after creation.

## Evidence layout

- `environment/`: environment, RBAC and seven CLI help records
- `success/`: seven-command success transcript, final cluster state and artifacts
- `application-failure/`: seven-command exit-7 transcript and retained artifacts
- `collector-failure/`: seven-command stats-failure transcript and diagnostics
- `tests.stdout`, `tests.stderr`, `tests.exit-code`, `tests.meta`: test evidence

Each CLI execution has `.meta`, `.stdout`, `.stderr` and `.exit-code` records.
Each Kubernetes path contains final Job/Pod YAML, container exit codes,
metadata checks and post-clean verification.

## Non-blocking observations

- The k3s kubectl wrapper emits `/etc/rancher/k3s/config.yaml.d` permission
  warnings. API operations and RBAC checks remain successful; permissions were
  not changed.
- GPU allocation is time-sliced `nvidia.com/gpu.shared`, so this is integration
  evidence rather than an exclusive performance benchmark.

## Deferred release-engineering item

- Before formal versioned delivery, re-run the suite from a real Git worktree
  and record `git rev-parse HEAD`. This does not block Phase 5 or Phase 6.
