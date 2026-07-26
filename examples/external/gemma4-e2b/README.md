# Gemma 4 E2B Phase 6 Example

This is the single additional non-YOLO workload required by the revised Phase
6A scope. It profiles bounded CUDA text generation with the external
`unsloth/gemma-4-E2B-it-qat-w4a16` model.

The selected checkpoint is an inference-oriented compressed format. This
example validates external LLM compatibility and profiling; it is not a
fine-tuning or training claim.

## Files

- `gx10-source-job.yaml`: source `batch/v1` Job accepted by Builder;
- `provenance.md`: model URL, immutable revision, weights metadata and scope.

## GX10 prerequisites

- Kubernetes namespace `profiling`;
- node `gx10-c206`;
- `runtimeClassName: nvidia`;
- one `nvidia.com/gpu.shared` allocation;
- pre-created `profile-artifacts` PVC;
- outbound model/package download access;
- sufficient ephemeral storage for the model and runtime dependencies.

The source Job must be passed through Builder. Do not submit it as the Profile
Job itself.

The accepted run and exact seven-command transcripts are recorded under:

`evidence/phase-6/20260726-132018/gemma4-e2b/`
