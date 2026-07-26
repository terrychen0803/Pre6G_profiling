# Profile Job Builder

將使用者的 Kubernetes Job 轉換為獨立的 NVIDIA Nsight Systems Profile Job，以產生、解析、保存並查看 CPU–GPU execution profile。

## 目前可用成果

目前已完成：

- 凍結目標與驗收規格：[`docs/TARGET_SPEC.md`](docs/TARGET_SPEC.md)
- 動態進度與 blockers：[`docs/PROGRESS_TRACKER.md`](docs/PROGRESS_TRACKER.md)
- `inspect`、`validate`、`build`、`diff`、`run`、`collect`、`clean` CLI
- Offline unit and transformation integration tests：45/45 passed
- Ultralytics YOLO26n + synthetic 小型資料集單 GPU短訓練範例
- 手寫與 Builder 產生的 Profile Job YAML
- `gx10-c206` host Nsight smoke test：實際產生並解析 CUDA `.nsys-rep`
- GX10 Kubernetes context/API/RBAC 驗證完成；reference node 為 Ready
- GX10 GPU resource 已確認為 `nvidia.com/gpu.shared=4`
- 非特權 Kubernetes Pod hostPath smoke test 已通過（UID 65532、Nsight
  Systems 2025.3.2）
- Kubernetes YOLO26n shared-GPU training 已完成；trainer/collector exit 0
- 已產生並解析 4,098,639-byte `.nsys-rep`，包含 CUDA API、GPU kernel、
  GPU memory operations 與 OS runtime summaries
- Collector failure matrix 已通過：missing、empty、invalid、truncated、
  checksum mismatch、partial stats、application failure 均不會誤判成功
- Nsight Systems 2025.3.2 GUI 人工驗收已通過：report 可開啟且 primary
  YOLO process 具有 CUDA、NVTX 與 OS Runtime traces

Phase 1 與 Phase 2 已完整通過。
`profiling/profile-artifacts` 已由管理者建立並驗證為 Bound（20Gi、RWO、
`local-path`），且 YOLO26 Profile Pod 刪除後 readback Pod 仍能讀回相同
report checksum。Phase 3 GUI 為 PASS with non-blocking limitations；Phase 4
failure matrix 已完成。Phase 5 的成功、application exit 7 與 collector
stats failure 三條真實 Kubernetes E2E 均功能 PASS，並有七 CLI
transcripts、metadata、artifact 與 clean 證據，因此 Phase 5 已完成。
本次驗收以 source-tree SHA-256 綁定；Git commit provenance 延後至正式
版本交付前補充，不阻塞 Phase 6 外部使用者 YAML 驗收。

GX10 工程 smoke test 使用 `nvidia.com/gpu.shared: "1"`。此結果只驗證
profile pipeline，不代表獨占 GPU 效能基準。

## 預定工作流程

```text
user-job.yaml
  → inspect / validate
  → build profile-job.yaml
  → human diff review
  → run on gx10-c206
  → collect artifacts
  → nsys stats / Nsight Systems GUI
```

## Artifact 結構

完成 Phase 4 後，每次執行預計輸出：

```text
artifacts/<profile-job-name>/
├── profile.nsys-rep
├── nsys-stats.txt
├── nsys-stats.csv
├── profile-metadata.json
├── application.log
└── profile-job.yaml
```

強化後 Kubernetes YOLO26 成功 artifacts 位於
`artifacts/yolo26-train-profile-phase4-run2/`；該 report 已通過 CLI
結構化解析與 Nsight Systems 2025.3.2 GUI 人工驗收。

GUI 驗收的已知非阻塞限制：目前未收集 scheduler trace，因此 CPU
utilization 僅由 OS Runtime 推估；Unified Memory tracing 不受目前
driver/config 支援；非 CUDA auxiliary PID 117 沒有 CUDA/NVTX events，
但 primary workload PID 96 的 traces 完整。

## Local Quick Start

建立虛擬環境與安裝：

```bash
python3 -m venv .venv
.venv/bin/pip install -e . pytest
```

檢查 YOLO26 使用者 Job：

```bash
.venv/bin/profile-job-builder inspect \
  --input examples/yolo26/user-job.yaml \
  --container trainer

.venv/bin/profile-job-builder validate \
  --input examples/yolo26/user-job.yaml \
  --container trainer
```

產生並審查獨立 Profile Job：

```bash
.venv/bin/profile-job-builder build \
  --input examples/yolo26/user-job.yaml \
  --container trainer \
  --name yolo26-train-profile-20260724-01 \
  --artifact-pvc profile-artifacts \
  --output profile-job.yaml

.venv/bin/profile-job-builder diff \
  --input examples/yolo26/user-job.yaml \
  --container trainer
```

執行 tests：

```bash
.venv/bin/pytest
```

執行 reference-node preflight：

```bash
nvcc -O2 scripts/cuda-smoke.cu -o /tmp/profile-job-builder-cuda-smoke
scripts/node-preflight.sh \
  --skip-kubernetes \
  --cuda-command /tmp/profile-job-builder-cuda-smoke
```

## Kubernetes Quick Start

目前 kubeconfig、context 與 server-side dry-run 已驗證。

PVC 已建立；以下是新環境重建時才需要的管理者步驟。不可使用
`profile-job-builder.kubeconfig`，因為該 ServiceAccount 按設計沒有 PVC
get/create 權限：

```bash
kubectl --kubeconfig <admin-kubeconfig> apply \
  -f /home/good_egg/profile-job-builder/examples/storage/profile-artifacts-pvc.yaml
kubectl --kubeconfig <admin-kubeconfig> \
  -n profiling get pvc profile-artifacts
```

PVC 顯示 `Bound` 後，再以受限的 Profile Job ServiceAccount 執行：
每次執行必須使用新的 `--name`，避免重用持久化 artifact 目錄。

```bash
cd /home/good_egg/profile-job-builder
export KUBECONFIG=/home/good_egg/.kube/profile-job-builder.kubeconfig
kubectl config current-context

.venv/bin/profile-job-builder run \
  --input profile-job.yaml \
  --kubeconfig /home/good_egg/.kube/profile-job-builder.kubeconfig \
  --context profile-job-builder@k3s \
  --namespace profiling

.venv/bin/profile-job-builder collect \
  --job yolo26-train-profile-20260724-01 \
  --container trainer \
  --profile-job-yaml profile-job.yaml \
  --kubeconfig /home/good_egg/.kube/profile-job-builder.kubeconfig \
  --context profile-job-builder@k3s \
  --namespace profiling \
  --destination artifacts/yolo26-train-profile-20260724-01

kubectl wait \
  --for=condition=complete \
  --timeout=120s \
  job/yolo26-train-profile-20260724-01

.venv/bin/profile-job-builder clean \
  --job yolo26-train-profile-20260724-01 \
  --kubeconfig /home/good_egg/.kube/profile-job-builder.kubeconfig \
  --context profile-job-builder@k3s \
  --namespace profiling
```

## 第一階段限制

- 僅支援 Kubernetes `batch/v1 Job`
- 單 application container、單一 GPU allocation、單節點
- GX10 工程 smoke test 使用 `nvidia.com/gpu.shared: "1"`；不支援以 shared
  GPU 結果宣稱獨占效能基準
- GX10 application Pod 使用 `runtimeClassName: nvidia`
- 固定 reference node：`gx10-c206`
- Reference workload namespace：`profiling`
- Linux ARM64 application image
- application command 必須明確存在於 YAML 或完整由 CLI 提供
- 不使用 PID attach、`hostPID`、`shareProcessNamespace`、`SYS_PTRACE` 或 privileged container
- `collect` 使用既有 Profile Pod 的 logs/exec，不建立 helper Pod；不需要
  `create pods` 權限
- 不含 HPCToolkit、Nsight Compute、MPI、多節點、controller 或 admission webhook

## 官方參考

- [NVIDIA Nsight Systems](https://developer.nvidia.com/nsight-systems)
- [Nsight Systems Documentation](https://docs.nvidia.com/nsight-systems/)
- [Ultralytics YOLO26](https://docs.ultralytics.com/models/yolo26/)
- [HPCToolkit](https://hpctoolkit.org/)
