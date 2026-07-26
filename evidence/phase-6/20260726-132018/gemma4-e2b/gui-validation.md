# Phase 6 Gemma GUI Validation

Status: **Deferred / Non-blocking**

Report:
`artifacts/profile.nsys-rep`

Expected report identity:

- size: `24,280,116` bytes
- SHA-256:
  `f434dfe3ca2768ce648d5990023f4a3e1b8036b49355ef37b12de0b664a50091`
- producer/collector/local checksum agreement: PASS
- CLI parsing and required summaries: PASS

Use Nsight Systems 2025.3.2 or a report-compatible newer GUI.

This optional checklist is retained for future interactive analysis. It is not
part of the current Phase 6 technical-validation completion gate.

## Optional review checklist

- [ ] Report opens without corruption error.
- [ ] Report opens without version incompatibility error.
- [ ] Primary Gemma/Python application process is identifiable.
- [ ] CUDA API track is visible.
- [ ] GPU kernel track is visible.
- [ ] A CUDA API launch can be correlated with GPU kernel execution.
- [ ] GPU stream and memory-operation tracks are visible.
- [ ] CPU thread and OS Runtime activity are inspectable.
- [ ] Timeline zoom, pan and event selection work.
- [ ] Messages are classified as blocking or non-blocking below.

## Evidence files

Save screenshots under `gui/`:

1. `01-overall-timeline.png`
2. `02-cuda-api-kernel-correlation.png`
3. `03-gpu-memory-operations.png`
4. `04-cpu-os-runtime.png`
5. `05-messages-and-limitations.png`

## Review record

- GUI version:
- Reviewer:
- Review date:
- Primary process:
- Blocking warnings:
- Non-blocking warnings:
- Overall result: `DEFERRED`
