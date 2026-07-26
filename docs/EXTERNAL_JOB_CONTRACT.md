# Phase 6 External AI Workload Compatibility Contract

Status: Frozen for Phase 6A
Contract version: v1
Effective date: 2026-07-26
Parent specification: `docs/TARGET_SPEC.md` v1.2

## 1. Purpose

Phase 6 validates that Profile Job Builder is framework-agnostic within the
existing frozen structural boundary. It does not claim compatibility with
arbitrary Kubernetes YAML.

An accepted external workload must not be derived from the repository's YOLO26
fixture. Builder must transform it without modifying or executing the source
Job, preserve its application semantics, and complete the following chain:

```text
external-model batch/v1 Job
  → inspect / validate / build / diff
  → independent Profile Job
  → Kubernetes GPU execution on gx10-c206
  → valid Nsight report and required stats
  → persistent and locally collected artifacts
  → CLI structured report analysis
  → clean
```

“Framework-agnostic” means the Builder does not depend on YOLO-, PyTorch-,
TensorFlow-, JAX- or launcher-specific fields. It does not mean the input
structure is unrestricted.

## 2. External provenance

A positive Phase 6 case is external only when all of the following are
recorded:

- the model or application is independently maintained outside this Builder;
- provenance is recorded as a model/application URL and immutable revision or
  supplied file identifier;
- the source YAML was not derived from `examples/yolo26/` or
  `fixtures/phase-5/`;
- source YAML SHA-256 is recorded before inspection;
- any adaptation needed for GX10 is recorded as a separate patch and never
  presented as the untouched upstream source.

One additional positive external-model case is required. Phase 6A uses
`unsloth/gemma-4-E2B-it-qat-w4a16`, requested by the project user and maintained
outside this repository.

## 3. Layer 1 — Core safety contract

These rules are not environment-specific:

- input is exactly one YAML document;
- input is `apiVersion: batch/v1`, `kind: Job`;
- Phase 6 invocation explicitly supplies the target container;
- target command and argument vector are explicit in YAML, or supplied in full
  through `--entrypoint` and repeated `--arg`;
- source YAML is neither modified nor submitted;
- transformation is deterministic and reviewable with `diff`;
- `hostPID`, `shareProcessNamespace`, privileged containers and `SYS_PTRACE`
  are forbidden;
- Builder-reserved container, volume and mount names must not conflict;
- source application exit semantics must be preserved;
- unsupported or ambiguous inputs are rejected without a partial output file.

## 4. Layer 2 — Workload compatibility contract

### 4.1 Supported Phase 6A subset

- one application container and no pre-existing regular sidecar;
- zero or more non-conflicting init containers;
- one GPU limit using exactly one supported resource:
  `nvidia.com/gpu.shared: "1"` or `nvidia.com/gpu: "1"`;
- matching GPU request may be omitted or equal to one;
- Linux ARM64 application image;
- a bounded CUDA AI workload that terminates within the acceptance timeout;
- exec-form command and args, including an explicit shell command when the
  source workload intentionally uses shell semantics;
- source `env`, `envFrom`, `workingDir`, `imagePullPolicy`, `resources`,
  `securityContext`, volume mounts and Pod volumes;
- non-conflicting `emptyDir`, PVC, ConfigMap and Secret volumes;
- Pod scheduling and identity fields such as `serviceAccountName`,
  `imagePullSecrets`, `tolerations`, `affinity`, `schedulerName` and
  `priorityClassName`, subject to the GX10 placement rules below.

### 4.2 Unsupported Phase 6A inputs

- Pod, Deployment, CronJob, MPIJob, PyTorchJob or another non-`batch/v1 Job`;
- multiple regular application containers or an existing sidecar;
- ephemeral containers;
- CPU-only workload, zero GPU, more than one GPU, or mixed shared/dedicated GPU
  resources;
- multi-node or multi-GPU distributed training;
- long-running service or an unbounded workload;
- automatic inference of image `ENTRYPOINT` or `CMD`;
- dynamic PID attach;
- an existing RuntimeClass other than `nvidia`;
- a hostname selector other than `gx10-c206`;
- Builder-reserved names or mount paths.

### 4.3 Static validation versus execution preconditions

The current Builder can validate structure, explicit command/args, GPU resource
shape, forbidden privileges, reserved conflicts, RuntimeClass conflicts and
hostname conflicts.

The following cannot be proven from YAML alone and must be established through
provenance, preflight or Kubernetes E2E evidence:

- the image is Linux ARM64 and pullable by the cluster;
- the image contains the requested framework and command;
- referenced PVCs, ConfigMaps and Secrets exist;
- the workload actually executes CUDA kernels;
- the workload terminates within the configured timeout;
- its application-level training result is meaningful.

Passing `validate` therefore means “safe to transform under the structural
contract,” not “guaranteed to execute successfully.”

## 5. Layer 3 — GX10 environment profile for Phase 6A

Phase 6A uses the existing frozen v1.2 environment behavior:

- namespace: `profiling`;
- node: `gx10-c206`;
- RuntimeClass: `nvidia`;
- GPU resource available on this cluster: `nvidia.com/gpu.shared`;
- GPU allocation: one shared GPU;
- Nsight host path: `/opt/nvidia/nsight-systems/2025.3.2`;
- Nsight mount path: `/opt/profiler/nsys`;
- artifact PVC: `profile-artifacts`;
- artifact mount path: `/profile-output`;
- collector/init image: immutable ARM64 Ubuntu image already used by Builder;
- application and collection acknowledgement timeout: 3600 seconds.

A declarative `ProfileEnvironment`, `--environment` CLI option and environment
schema are deferred to v2. Introducing them during Phase 6A would test a new
configuration subsystem rather than isolate external-workload compatibility.

## 6. Preservation contract

### 6.1 Fields that must be identical

The transformation must preserve:

- application `name` and `image`;
- `imagePullPolicy`;
- `workingDir`;
- user-provided `env` and `envFrom`, except that Builder upserts its reserved
  `TMPDIR` and `PROFILE_OUTPUT_DIR`;
- `resources`, including the declared GPU resource;
- application `securityContext`;
- existing application `volumeMounts`, in the same order;
- existing Pod `volumes`, in the same order;
- existing init containers, in the same order;
- Pod `securityContext`;
- `serviceAccountName`, `imagePullSecrets`, `tolerations`, `affinity`,
  `schedulerName` and `priorityClassName`;
- original command and argv boundaries as recorded in the Builder annotation
  and passed after the wrapper's `--`.

### 6.2 Controlled changes

Builder may:

- change `metadata.name`;
- remove server-managed metadata, status, owner references and unsafe
  selectors;
- add profiling labels and annotations;
- set `backoffLimit: 0`, `parallelism: 1`, `completions: 1` and
  `restartPolicy: Never`;
- set the GX10 hostname selector and `runtimeClassName: nvidia`, rejecting
  conflicting source values;
- replace the target command/args with the `nsys profile` wrapper while
  preserving the original argv after `--`;
- upsert `TMPDIR` and `PROFILE_OUTPUT_DIR`;
- append `profile-output-init` after source init containers;
- append `profile-collector` after the profiled application;
- append `nsys-runtime` and `profile-output` volumes and mounts.

The source file checksum before and after transformation must be identical.

## 7. Positive compatibility matrix

Phase 6 completion requires one E2E-positive external-model case:

| ID | Pattern | Required distinguishing coverage | Gate |
|---|---|---|---|
| E1 | Transformers Gemma 4 E2B bounded generation | external 8.32 GB LLM, init dependency installation, model cache, env, workingDir and CUDA generation | Required |

The selected `w4a16` checkpoint is an optimized compressed inference format.
The case validates a bounded external LLM workload and must not be described as
fine-tuning or training.

## 8. Negative compatibility matrix

All five offline rejection cases are required:

| ID | Input | Expected result |
|---|---|---|
| N1 | missing command or args | reject with actionable command/args error |
| N2 | privileged or `SYS_PTRACE` | reject with safety error |
| N3 | two regular containers | reject as unsupported structure |
| N4 | GPU limit equals two | reject under v1 |
| N5 | reserved `/profile-output` mount or reserved name | reject conflict |

For every rejection:

- `inspect`, `validate` or `build` returns nonzero as applicable;
- stderr identifies the violated rule;
- no Profile Job is submitted;
- `build --output` does not leave a partial output file.

## 9. Completion gate

Phase 6 is Done only when:

- [x] one additional non-YOLO external-model Job is recorded;
- [x] the Gemma 4 E2B bounded generation case completes E2E;
- [x] source provenance and source SHA-256 are recorded;
- [x] `inspect`, `validate`, `build`, `diff`, `run`, `collect` and `clean`
  transcripts are present for each positive case;
- [x] source checksum is unchanged after transformation;
- [x] automated field-preservation comparison passes;
- [x] Kubernetes server dry-run passes;
- [x] Profile Pod runs on `gx10-c206` with one shared GPU;
- [x] application and collector exit zero and Job condition is Complete;
- [x] six mandatory success artifacts are present and non-empty;
- [x] producer, collector and local report checksums agree;
- [x] required CUDA API, GPU kernel, GPU MemOps and OS Runtime summaries exist;
- [x] each positive report passes CLI structured parsing and required-summary
  validation;
- [x] clean removes the Job and Pods while retaining local artifacts;
- [x] N1–N5 are rejected without submission or partial output;
- [x] a consolidated Phase 6 acceptance report is complete.

GUI timeline review is deferred and non-blocking for the current technical
validation milestone. The `.nsys-rep` remains preserved for future GUI use.

## 10. Deferred v2 work

The following are explicitly not Phase 6A completion requirements:

- declarative Cluster Environment Profile and `--environment`;
- multiple regular containers or sidecar policies;
- multi-GPU or multi-node workloads;
- automatic image ENTRYPOINT/CMD resolution;
- non-Job workload kinds;
- HPCToolkit or another profiler backend.
