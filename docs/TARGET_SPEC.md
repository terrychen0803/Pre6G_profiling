# Profile Job Builder — Target Specification

> 狀態：Frozen  
> 基線版本：v1.2  
> 凍結日期：2026-07-24  
> 變更規則：除非第一階段技術路線無法成立，否則不得修改本文件。執行狀態與問題只能更新於 `PROGRESS_TRACKER.md`。
>
> 受控修訂：v1.1（2026-07-24）依實際 cluster resource contract，將 GX10
> 工程 smoke test 的 GPU resource 改為 `nvidia.com/gpu.shared: "1"`。
> Cluster 未提供 `nvidia.com/gpu`，因此本階段不宣稱獨占 GPU 效能基準成立。
>
> 受控修訂：v1.2（2026-07-24）依 cluster smoke test，GX10 application Pod
> 必須使用 `runtimeClassName: nvidia`；僅請求 shared GPU resource 不會將
> CUDA device 注入容器。

## 1. North Star

對使用者提交的 Kubernetes `batch/v1 Job` YAML 建立一份獨立、可供人工審查的 Profile Job。在不修改應用程式原始碼、不修改或執行原始正式 Job 的前提下，由 NVIDIA Nsight Systems CLI 啟動指定的 application container command，完成以下鏈路：

```text
User Job YAML
  → Profile Job Builder
  → Independent Profile Job YAML
  → Kubernetes Job on gx10-c206
  → nsys profile launches the original command
  → profile.nsys-rep
  → nsys stats
  → persistent artifacts
  → Nsight Systems GUI
```

第一個 reference workload 為單一 shared GPU allocation 的 Ultralytics YOLO26n
訓練，使用小型資料集與短訓練週期驗證工程鏈路，不用於模型品質或效能基準比較。

## 2. 第一階段輸入契約

- API：`batch/v1`、kind：`Job`。
- YAML 必須只包含一個文件。
- 使用者必須明確指定一個 application container。
- Pod 只支援一個 application container；含既有 sidecar 的 Job 第一版拒絕處理。
- application container 必須：
  - 在 YAML 中同時提供非空 `command` 與 `args`；或
  - 由 Builder CLI 提供完整 entrypoint 與 arguments。
- GX10 工程 smoke test 使用且僅使用一個 `nvidia.com/gpu.shared`。
- Builder 仍可辨識未來 cluster 的 `nvidia.com/gpu: "1"`，但 shared 與 dedicated
  resource 不得同時出現；目前 GX10 不提供 dedicated resource。
- application image 與 Nsight Systems Target CLI 必須同為 Linux `arm64`。
- 輸入不得使用 `hostPID`、`shareProcessNamespace`、privileged container 或 `SYS_PTRACE`。
- 輸入不得占用 Builder 保留的名稱與路徑：
  - volume：`profile-output`、`nsys-runtime`
  - mount path：`/profile-output`、`/opt/profiler/nsys`
  - container：`profile-collector`

不符合契約時 Builder 必須失敗並提供可操作的錯誤訊息，不可輸出部分轉換結果。

## 3. Profile Job 轉換契約

Builder 必須：

1. 深拷貝輸入 Job，不改寫原檔。
2. 移除 server-managed metadata、`status`、owner reference 及不可安全複製的 selector。
3. 產生 DNS-compatible 且可辨識的獨立 Job 名稱。
4. 加入 profiling labels/annotations。
5. 以 `kubernetes.io/hostname: gx10-c206` 固定 reference node。
6. 設定 `runtimeClassName: nvidia`；若來源指定其他 RuntimeClass 則拒絕轉換。
7. 保留 application image、environment、GPU resource、working directory、security context，以及不衝突的 volume/mount。
8. 掛載 read-only Nsight Systems Target CLI `hostPath`。
9. 建立 application 與 collector 共用的 output volume。
10. 以 `nsys profile` 直接啟動原始 command，不使用 PID attach。
11. 關閉 CPU sampling；收集 CUDA、NVTX 與 OS runtime trace。
12. 注入不請求 GPU 的 collector，並在 collector 掛載相同的 Nsight runtime。
13. 設定 `restartPolicy: Never`，並提供有界等待與明確失敗狀態。
14. 輸出 Profile Job YAML 供人工檢查；除非使用者執行 `run`，不得自動提交 Kubernetes。

## 4. Artifact 契約

每次成功執行至少包含：

```text
profile.nsys-rep
nsys-stats.txt
nsys-stats.csv
profile-metadata.json
application.log
profile-job.yaml
```

`.nsys-rep` 必須非空且可由 `nsys stats` 成功解析。Phase 4 前必須確定持久化策略；`emptyDir` 只能作為 Pod 內交換空間，不視為持久保存。

`profile-metadata.json` 至少記錄：

- source/profile Job name
- namespace
- target container 與 image
- node name
- Nsight Systems version
- workload command
- start/end timestamp
- application、profiler、collector exit status
- GPU resource name 與 shared/dedicated mode
- artifact size 與 checksum

## 5. 系統架構

```text
┌────────────── Management workstation ──────────────┐
│ profile-job-builder                                │
│ inspect → validate → build → diff → run → collect  │
└───────────────────────┬────────────────────────────┘
                        │ Profile Job YAML
                        ▼
┌──────── Kubernetes node: gx10-c206 ────────────────┐
│ ┌──────────────── Profile Job Pod ───────────────┐ │
│ │ Application container                         │ │
│ │ /opt/profiler/nsys/bin/nsys profile           │ │
│ │   └─ original YOLO26/user command             │ │
│ │             └─ /profile-output/profile.nsys-rep│ │
│ │                                                │ │
│ │ Collector (no GPU, no PID attach)              │ │
│ │ wait (bounded) → validate → stats → metadata   │ │
│ │ → wait for management-side collection ack      │ │
│ │                                                │ │
│ │ shared output volume + read-only nsys hostPath │ │
│ └───────────────────┬────────────────────────────┘ │
└─────────────────────┼──────────────────────────────┘
                      ▼
             Persistent artifact location
                      │
             ┌────────┴────────┐
             ▼                 ▼
       nsys stats output   Nsight Systems GUI
```

## 6. 第一階段 Scope Boundary

第一階段不處理：

- warm-up 與週期偵測
- shared GPU 環境下的獨占效能基準、跨執行效能比較或可重現性宣稱
- 動態開始或停止 profiling
- CPU sampling、CPU hardware counters 或必須放寬 Pod 權限的 CPU scheduler tracing
- Nsight Compute
- HPCToolkit backend
- MPI、多 GPU或多節點 profiling
- 跨節點特徵抽取與執行時間預測
- CRD、controller、operator 或 admission webhook
- Deployment、Pod、CronJob 等非 Job 輸入
- 自動解析 container image 的 ENTRYPOINT/CMD
- 已含 sidecar 的使用者 Job

## 7. Phase 1–6 驗收標準

### Phase 1 — Reference node

- 在 `gx10-c206` 記錄 architecture、Nsight version、Target CLI path 與 `nsys status --environment`。
- Target CLI 可由非特權使用者執行。
- 確認 Kubernetes 可掛載路徑及 application/collector UID 權限。
- 簡單 CUDA workload 可在 node host 產生非空 `.nsys-rep`。
- 確認 YOLO26 application image 為可用的 Linux ARM64 GPU image，並記錄 immutable digest。

### Phase 2 — Manual Profile Job

- YOLO26 Pod 排程至 `gx10-c206` 並取得一個
  `nvidia.com/gpu.shared` allocation。
- `nsys` 直接啟動 YOLO26 training command。
- training 正常完成並產生非空 `.nsys-rep`。

### Phase 3 — Parse and view

- `nsys stats` 成功。
- CUDA API、GPU kernel、memory operation 與 OS runtime summaries 可取得。
- 沒有 NVTX 時允許 NVTX summary 為空。
- GUI 可開啟 report，顯示 process/thread、CUDA API、GPU kernel、stream、memory copy 與 synchronization timeline。

### Phase 4 — Collector and persistence

- collector 不使用 GPU、PID namespace 或額外 privilege。
- collector 不讀取未完成的 report，等待有 timeout。
- application 成功、失敗與 report 缺失時，Job 都能終止並回報正確狀態。
- artifacts 在 Pod 刪除後仍可取得。

### Phase 5 — Builder CLI

- 提供 `inspect`、`build`、`diff`、`validate`、`run`、`collect`、`clean`。
- 保留契約指定欄位，拒絕不安全或不支援輸入。
- 輸出 deterministic、可人工審查的 YAML。
- 自動化測試覆蓋成功路徑、衝突、缺欄位及禁止權限。

### Phase 6 — External Job

- 對非本專案產生、但符合輸入契約的 Job 完成端到端驗證。
- 原始 Job 不被修改或執行。
- Profile Job 保留 application 行為、environment、volumes 與 GPU resource。
- 完整產生、解析、保存並以 GUI 查看 CPU–GPU system timeline。

## 8. 第一階段最終完成定義

Phase 1–6 的所有驗收項目均有實際命令輸出或 artifact 證據；僅完成程式、單元測試、dry-run 或 YAML validation 不等同端到端完成。
