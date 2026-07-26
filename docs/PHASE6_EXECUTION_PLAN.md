# Phase 6 Execution Plan

Status: Complete — CLI-parseable technical validation
Prepared: 2026-07-26
Contract: `docs/EXTERNAL_JOB_CONTRACT.md`

## 1. Stage plan

### Phase 6.0 — Freeze compatibility contract

- [x] define external provenance;
- [x] define supported and unsupported v1 subset;
- [x] separate static validation from E2E preconditions;
- [x] define preserved and Builder-controlled fields;
- [x] define positive, negative and completion matrices.

### Phase 6.1 — External workload intake

- [x] record the user-selected external model and immutable revision;
- [x] create a non-YOLO bounded Job for the external model;
- [x] save source Job SHA-256;
- [x] confirm the Job satisfies the frozen v1.2 contract.

Files belong under:

```text
examples/external/<case-id>/
├── gx10-source-job.yaml
├── provenance.md
└── README.md
```

The Phase 6A case is `examples/external/gemma4-e2b/`. The external component is
the user-selected Unsloth model; the Kubernetes Job is the project's explicit,
reviewable execution description and is not claimed to be an upstream manifest.

### Phase 6.2 — Offline compatibility verification

- [x] add a reusable field-preservation comparator;
- [x] verify source YAML is not mutated;
- [x] verify deterministic build output;
- [x] verify original argv boundaries after the wrapper's `--`;
- [x] cover env, envFrom, workingDir, source init containers, ConfigMap, Secret,
  PVC, emptyDir and Pod scheduling/identity fields represented in the corpus;
- [x] implement N1–N5 rejection fixtures;
- [x] verify rejected builds leave no partial output;
- [x] run the complete offline suite (53/53 passed) and bind it to a
  source-tree manifest checksum.

The comparator must compare structured YAML fields. A textual diff alone is not
sufficient because Builder intentionally changes command/args and adds
profiling resources.

### Phase 6.3 — Kubernetes E2E

Run positive cases sequentially with unique Job names. Do not submit the
untouched source Job.

For each case:

```text
record source checksum
  → inspect
  → validate
  → build
  → verify source checksum unchanged
  → diff and field-preservation review
  → run (includes server dry-run)
  → collect
  → wait for Job Complete
  → validate metadata, artifacts, summaries and checksum
  → save final Job/Pod state
  → clean
  → verify Job NotFound and Pods=0
```

`collect` occurs before waiting for Job Complete because the collector waits for
the management-side `.collected` acknowledgement before exiting.

The only required positive case is the bounded Gemma 4 E2B generation Job.

Abort a case before `run` if provenance, preservation comparison or server
dry-run fails.

### Phase 6.4 — CLI report acceptance（Done）

The E2E-positive `.nsys-rep` must be parsed from disk using `nsys stats`.
Acceptance requires:

- report validation returns zero and non-empty output;
- OS Runtime, CUDA API, CUDA GPU kernel and both GPU MemOps summaries exist;
- text and CSV exports are non-empty;
- metadata records `reportValid=true` and `statsComplete=true`;
- producer, collector and local SHA-256 values agree.

GUI inspection and screenshots are retained as optional future analysis, not a
Phase 6 technical-validation gate.

### Phase 6.5 — Completion and documentation release（Done）

- [x] complete the consolidated acceptance report;
- [x] mark every completion-gate item with an evidence path;
- [x] update `docs/PROGRESS_TRACKER.md` to Done;
- [x] update `README.md` with only the compatibility actually demonstrated;
- [x] do not modify frozen `docs/TARGET_SPEC.md` unless a fatal route change is
  discovered.

## 2. Evidence structure

Use `evidence/phase-6/`, with a hyphen consistent with the existing repository:

```text
evidence/phase-6/
├── acceptance.md
├── offline-tests.txt
├── negative/
│   ├── n1-missing-command/
│   ├── n2-forbidden-privilege/
│   ├── n3-multiple-containers/
│   ├── n4-two-gpus/
│   └── n5-reserved-mount/
├── gemma4-e2b/
│   ├── provenance.md
│   ├── source-job.yaml
│   ├── source-job.before.sha256
│   ├── source-job.after.sha256
│   ├── 01-inspect.*
│   ├── 02-validate.*
│   ├── 03-build.*
│   ├── 04-diff.*
│   ├── 05-run.*
│   ├── 06-collect.*
│   ├── 07-clean.*
│   ├── field-preservation.json
│   ├── job-final.yaml
│   ├── pods-final.yaml
│   ├── container-exit-codes.txt
│   ├── post-clean-verification.txt
│   ├── gui-validation.md
│   ├── gui/
│   └── artifacts/
```

Every recorded CLI call uses `.meta`, `.stdout`, `.stderr` and `.exit-code`
files, following the Phase 5 recorder convention.

## 3. Per-case automated acceptance checks

The acceptance harness must fail unless:

- source checksum before and after is equal;
- inspect identifies the expected image, command, args and GPU resource;
- validate and build exit zero;
- generated YAML is non-empty and passes server dry-run;
- field preservation comparison has no unexplained difference;
- application and collector container exits are zero;
- Job has Complete and not Failed;
- `overallStatus=success`, `reportValid=true`, `statsComplete=true` and
  `localChecksumMatch=true`;
- six mandatory artifacts are non-empty;
- all required summary headings are present;
- clean exits zero, Job is NotFound, Pod count is zero;
- local artifacts remain after clean.

## 4. Field-preservation comparison design

The comparator receives source YAML, generated Profile Job YAML and target
container name. It reports JSON containing:

```json
{
  "result": "pass",
  "preserved": [],
  "controlled_changes": [],
  "unexpected_changes": []
}
```

It must:

1. compare source and generated application fields before accounting for the
   wrapper;
2. reconstruct the original argv from the generated wrapper arguments and
   compare it element-by-element;
3. confirm existing env entries remain unchanged while reserved Builder entries
   are upserted;
4. confirm source mounts, volumes and init containers remain ordered prefixes
   of their generated lists;
5. compare Pod identity, scheduling and security fields;
6. classify only the controlled changes listed in the compatibility contract;
7. fail on every unclassified difference.

## 5. External-resource prerequisites

ConfigMaps, Secrets and workload PVCs referenced by an external Job are
prerequisites, not Builder outputs. For each E2E case:

- list the exact prerequisite object names without recording secret values;
- have an administrator pre-create objects when Builder RBAC cannot;
- record read-only existence checks where authorized;
- never copy Secret data into evidence;
- clean only the Profile Job and its Pods unless separate removal was explicitly
  authorized.

## 6. Decision rules

- A workload incompatibility discovered before submission is a valid safe
  rejection, not a Builder failure, when the contract and error are clear.
- A positive case that fails because its image, dataset or prerequisite is
  unavailable does not pass and must not be replaced by a claim based only on
  dry-run.
- A report without required CUDA kernel activity does not satisfy the positive
  AI training case even if the Job exits zero.
- Shared-GPU results validate compatibility only; they are not exclusive
  performance benchmarks.
- Environment Profile abstraction, sidecar preservation and multi-GPU support
  are v2 work and must not be introduced to make a Phase 6A case pass.

## 7. Immediate next actions

1. optionally open the preserved report in Nsight Systems GUI for interactive
   performance analysis;
2. formally version the project in a Git worktree before release.
