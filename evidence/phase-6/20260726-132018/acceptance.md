# Phase 6 Gemma 4 E2B Acceptance

Status: **PASS — CLI-parseable technical validation**

Acceptance date: 2026-07-26
Kubernetes context: `profile-job-builder@k3s`
Namespace: `profiling`
Node: `gx10-c206`
Job: `phase6-gemma4-20260726-132018`

## Scope

Per project decision, Phase 6A requires one additional non-YOLO external-model
case rather than two. The selected case uses
`unsloth/gemma-4-E2B-it-qat-w4a16` revision `123e194` for bounded CUDA text
generation. The selected `w4a16` checkpoint is an inference-oriented compressed
format; this evidence does not claim fine-tuning or training.

## Result summary

| Gate | Result | Evidence |
|---|---|---|
| External provenance | PASS | `examples/external/gemma4-e2b/provenance.md` |
| Source YAML immutable | PASS | Before/after SHA-256 both `112f4fd2acf71bb806f3405c13c4a66de7dabe59546855d9971b78dcf60c58fc` |
| Seven CLI commands | PASS | `gemma4-e2b/01-inspect.*` through `07-clean.*`, all exit 0 |
| Field preservation | PASS | `field-preservation.json`: 20 preserved checks, no unexpected changes |
| Server dry-run | PASS | `server-dry-run.exit-code`: 0 |
| N1–N5 safe rejection | PASS | `negative/*/verify.*`; each pytest assertion passed and no partial output remained |
| Offline test suite | PASS | 53/53 in `offline-tests.txt` |
| Source-tree traceability | PASS | `source-tree.manifest` and `source-tree.sha256` |
| Kubernetes placement | PASS | `profile-metadata.json`: node `gx10-c206`, shared GPU resource |
| Application and collector | PASS | Both containers exited 0; Job reached Complete |
| External LLM execution | PASS | `application.log` contains `phase6-gemma4-complete` and generated text |
| Required artifacts | PASS | Six mandatory files are present and non-empty |
| Report validity and integrity | PASS | Metadata reports valid/complete/success and all three report checksums agree |
| Required Nsight summaries | PASS | OS Runtime, CUDA API, CUDA kernels and both GPU MemOps summaries |
| Independent report readback | PASS | Host `nsys stats --report=cuda_api_sum` exit 0 with 4,212-byte output |
| Clean | PASS | Job NotFound, Pods 0, local report retained |
| CLI report parsing | PASS | Report parsed to non-empty TXT/CSV/SQLite and all required summaries |
| GUI timeline | Deferred | Non-blocking for the current technical-validation milestone |

## Profile result

- profile report size: `24,280,116` bytes
- profile report SHA-256:
  `f434dfe3ca2768ce648d5990023f4a3e1b8036b49355ef37b12de0b664a50091`
- application profiler exit code: `0`
- collector exit code: `0`
- overall status: `success`
- report valid: `true`
- stats complete: `true`
- local checksum match: `true`
- GPU allocation: `nvidia.com/gpu.shared: "1"`

The expected producer checksum, collector checksum and locally calculated
checksum are identical.

The final Phase 6 source/docs/tests corpus is bound by a deterministic manifest
stored as `source-tree.manifest`. Its SHA-256 is recorded in
`source-tree.sha256`:
`02071d186346e1dc5343669dcd148c2dd023c3b147a2d38c3de15c1f684c81e2`.

## Required artifacts

| Artifact | Size |
|---|---:|
| `profile.nsys-rep` | 24,280,116 bytes |
| `nsys-stats.txt` | 37,145 bytes |
| `nsys-stats.csv` | 42,009 bytes |
| `profile-metadata.json` | 2,337 bytes |
| `application.log` | 9,370 bytes |
| `profile-job.yaml` | 15,275 bytes |

## Non-blocking observations

- The init container installed the Transformers/compressed-tensors dependency
  stack at runtime. This proves the case but adds download time and disk usage;
  a pinned prebuilt ARM64 image is preferable for release use.
- The Profile Job role cannot `get` the PVC. This is consistent with the
  established minimal RBAC model; the pre-created PVC and actual mount/write
  path succeeded.
- K3s emits the known
  `/etc/rancher/k3s/config.yaml.d: permission denied` warning. API access and
  the Job were unaffected, and host permissions were not changed.
- N3 correctly rejects multiple regular containers but currently reports
  secondary command/GPU validation messages after the primary structural
  error. This is a diagnostic-quality improvement, not a safety failure.

## Deferred interactive analysis

The report is retained and may later be opened with a compatible Nsight Systems
GUI. GUI screenshots are not required for the current Phase 6 acceptance.
