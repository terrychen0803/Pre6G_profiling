# Gemma 4 E2B Phase 6 provenance

- Requested by project user: 2026-07-26
- External model:
  <https://huggingface.co/unsloth/gemma-4-E2B-it-qat-w4a16>
- Publisher: Unsloth AI
- Model revision used by the acceptance Job: `123e194`
- License shown by model card: Apache-2.0
- Format: compressed-tensors `w4a16`
- Weight file size shown by repository: 8.32 GB
- Weight SHA-256 shown by repository:
  `93177bfc1b53823f2e01c7cebc3b94f65d189e373a647d086112f614ba448ab9`
- Application pattern: bounded Transformers text generation on one CUDA-visible
  shared GPU
- Job YAML author: Profile Job Builder project, implementing the external model
  workload requested by the user
- Not derived from the YOLO26 or Phase 5 fixtures

The model card identifies `w4a16` as an optimized compressed inference format.
This case validates external LLM workload compatibility and CUDA profiling; it
does not claim that the quantized checkpoint was fine-tuned by this Job.
