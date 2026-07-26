# Phase 4 collector reliability matrix

Date: 2026-07-24  
Production collector tests: `tests/test_collector_failures.py`  
Full offline suite: 45/45 passed

## Matrix

| Case | Expected classification | Collector result |
|---|---|---|
| Normal report | success | exit 0, `report_valid=true`, `stats_complete=true` |
| Report missing | `missing_report` | exit 20; no published stats |
| Report empty | `empty_report` | exit 21; no published stats |
| Non-Nsight content | `parse_failure` | exit 25; parser diagnostics retained |
| Truncated Nsight report | `corrupted_report` | exit 24; parser diagnostics retained |
| Producer/collector checksum mismatch | `integrity_failure` | exit 23; stats not invoked |
| Required stats command fails | `stats_failure` | exit 26; no published final stats |
| CSV export fails | `stats_failure` | exit 26; no published final stats |
| Tool exits 0 but emits export/database ERROR | `stats_failure` | exit 26 |
| Required summary heading missing | `stats_failure` | exit 26 |
| Application exit nonzero | `application_exit_nonzero` | valid report/stats retained; collector exit 27 |

Failure metadata records:

- `overall_status`
- `failure_reason`
- `application_exit_code`
- `report_exists`
- `report_size_bytes`
- `report_valid`
- `expected_checksum`
- `actual_checksum`
- `checksum_match`
- `stats_complete`
- `collector_exit_code`

The collector publishes `.collector-ready` for both success and failure so the
Builder can retrieve application logs, metadata, partial diagnostics and
`nsys-stats.stderr.txt`. It exits only after collection acknowledgement. The
Builder returns a nonzero result when `overall_status != success`.

## Real Nsight parser behavior

Nsight Systems 2025.3.2 was run against real invalid and truncated inputs:

```text
invalid:
Exportation error: Version tag is not found in the stream.
ERROR: Database file /tmp/not-valid.sqlite does not exist.

truncated:
Exportation error: Section Table Reference magic number mismatch.
ERROR: Database file /tmp/yolo-truncated.sqlite does not exist.
```

In both cases `nsys stats` returned process exit code 0. The production
collector therefore checks command status, non-empty output, error text in both
stdout/stderr, and the presence of every mandatory summary. Exit code alone is
not accepted as success.

## Kubernetes negative-path evidence

Job `yolo26-train-profile-phase4` exercised a real collector failure:

- application exit: 0
- producer/collector/local checksum: identical
- collector exit: 26
- `overallStatus`: failed
- `failureReason`: stats_failure
- Builder `collect`: nonzero with diagnostic artifact path
- Pod condition reason: `PodFailed`

Artifacts: `artifacts/yolo26-train-profile-phase4/`

## Kubernetes normal regression

Job `yolo26-train-profile-phase4-run2` passed after the final hardening:

- application exit: 0
- collector exit: 0
- Kubernetes Job: Complete
- report size: 4,249,649 bytes
- SHA-256:
  `06ad732795c40fea5f2081b4adba1bba01076113cd933e3092a535d1b554d781`
- expected/collector/local checksums: identical
- `reportValid`: true
- `statsComplete`: true
- stats stderr: 0 bytes
- OS Runtime, CUDA API, CUDA GPU Kernel and both CUDA GPU MemOps summaries:
  present

Artifacts: `artifacts/yolo26-train-profile-phase4-run2/`
