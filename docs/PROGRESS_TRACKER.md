# Profile Job Builder — Progress Tracker

> 最後更新：2026-07-26
> 當前狀態：Phase 0 至 Phase 5 已完成；Phase 5 三條 Kubernetes E2E
> 功能路徑皆 PASS，並以 source-tree SHA-256 綁定驗收內容。Git commit
> provenance 延後至正式版本交付前補充，不阻塞 Phase 6。Phase 6
> Gemma 4 E2B 外部模型的 CLI、offline、Kubernetes E2E 與 CLI report
> 結構化解析均已 PASS；GUI 依專案決策延後且不阻塞技術驗證。YOLO26 已在
> `gx10-c206` 使用 `runtimeClassName: nvidia` 與
> `nvidia.com/gpu.shared: "1"` 完成 training、Nsight report、stats、
> persistence 與 CLI collection；shared GPU 結果不視為獨占效能基準。

狀態定義：

- `[x]` Done：具有可重現的驗收證據。
- `[-]` In Progress：正在執行，尚未通過完整驗收。
- `[ ]` Todo：尚未開始或缺少必要證據。

## Phase checklist

### Phase 0 — Documentation contract

- [x] 建立凍結的 `docs/TARGET_SPEC.md`
- [x] 建立動態 `docs/PROGRESS_TRACKER.md`
- [x] 建立只描述目前成果的 `README.md`
- [x] 指定 YOLO26n + synthetic 小型資料集短訓練為 reference workload

### Phase 1 — Reference Node 環境確認（Done）

子階段狀態：

- Host 環境與 Nsight smoke test：Done
- YOLO26 ARM64 image manifest 驗證：Done
- Kubernetes 連線、Node 與 RBAC 驗證：Done
- Kubernetes Pod 內 hostPath mount smoke test：Done

- [x] 建立可重現的 node preflight 工具
- [x] 連線／操作 `gx10-c206`
- [x] 驗證 context `profile-job-builder@k3s`、API server 與最小 RBAC
- [x] 記錄 `uname -m`
- [x] 記錄 `nsys --version`
- [x] 記錄 `nsys status --environment`
- [x] 確認可掛載的 Nsight Target CLI 實際路徑
- [x] 驗證非特權 UID 的讀取與執行權限
- [x] 在 host 對 CUDA workload 產生非空 `.nsys-rep`
- [x] 確認 YOLO26 Linux ARM64 GPU image 與 immutable digest
- [x] Kubernetes Pod 內 hostPath mount／執行權限 smoke test
- [x] 保存 Phase 1 驗收證據

### Phase 2 — YOLO26 Profile Job（Done）

- [x] 建立原始 YOLO26 training Job 範例
- [x] 建立不含 collector 的手動 Profile Job
- [x] YAML schema／server dry-run 通過
- [x] 排程至 `gx10-c206`
- [x] application 取得一個 shared GPU allocation 並完成 training
- [x] 產生非空 `profile.nsys-rep`
- [x] failure-path application 仍產生非空、可收集的 `.nsys-rep`
- [x] 保存 Phase 2 驗收證據

### Phase 3 — 結果解析與 GUI（Done — PASS with non-blocking limitations）

- [x] Host CUDA smoke report 可由 `nsys stats` 成功解析
- [x] Kubernetes YOLO26 failure-path report 可由 `nsys stats` 成功解析
- [x] Kubernetes YOLO26 successful-training report 可由 `nsys stats` 成功解析
- [x] Host CUDA API summary
- [x] Host CUDA GPU kernel summary
- [x] Host CUDA memory operations summary
- [x] Host OS runtime summary
- [x] Kubernetes YOLO26 CUDA API、GPU kernel、memory 與 OS runtime summaries
- [x] Nsight Systems 2025.3.2 GUI 成功開啟 report，無損壞或版本不相容
- [x] GUI Session／Statistics、primary process/thread、GPU 與 analysis
  資訊可用
- [x] GUI 確認 primary PID 96 的 CUDA（163,464）、NVTX（439）與 OS
  Runtime（53,030）事件
- [x] 記錄 Unified Memory、CPU scheduling 與 auxiliary PID 117 的
  non-blocking limitations
- [x] 保存 Phase 3 CLI 與 GUI 人工驗收證據

### Phase 4 — Collector Sidecar（Done）

- [x] 定義並實作 report 完成判定與 timeout
- [x] collector manifest 不請求 GPU
- [x] collector manifest 不使用 PID attach 或額外 privilege
- [x] application 成功路徑通過（trainer/collector exit 0、Job Complete）
- [x] application 失敗路徑：保留有效 report/stats，collector exit 27，
  overall run failed
- [x] production collector failure classification 與 metadata 強化
- [x] report 不存在：`missing_report`
- [x] report 為 0 byte：`empty_report`
- [x] report 為非 Nsight 內容：`parse_failure`
- [x] report 被截斷：`corrupted_report`
- [x] producer／collector checksum 不一致：`integrity_failure`
- [x] 任一必要 stats report、summary 或 CSV export 失敗：`stats_failure`
- [x] application exit 非 0：保留 artifacts，overall run failed
- [x] collector exit 非 0：Kubernetes Pod/Job failure，Builder collect 非 0
- [x] failure metadata、partial diagnostics 與 stderr 可被 Builder 收集
- [x] PVC 持久化策略：`profiling/profile-artifacts`，20Gi RWO
  `local-path`
- [x] Pod 刪除後 artifacts 仍可取得
- [x] 保存 Phase 4 驗收證據

### Phase 5 — Profile Job Builder CLI（Done）

子階段狀態：

- CLI implementation：Done
- Offline verification：Done
- Kubernetes cluster integration：Done（成功、application exit 7
  與 collector stats failure 均執行完整七指令）
- Source-tree traceability：Done，以 SHA-256 綁定
- Git commit traceability：Deferred，非阻塞

- [x] `inspect`
- [x] `validate`
- [x] `build`
- [x] `diff`
- [x] `run`
- [x] `collect`
- [x] `clean`
- [x] deterministic YAML output
- [x] Offline unit and transformation integration tests：45/45 passed
- [x] Kubernetes cluster integration tests
- [x] 成功路徑七指令 transcript、完整 artifacts、checksum 與 clean 驗證
- [x] application exit 7 七指令 transcript、失敗傳遞與 artifacts 保留
- [x] collector exit 26 七指令 transcript、`stats_failure` 與診斷保留
- [x] 三條路徑 Job/Pod final YAML、container exits 與 metadata 驗證
- [x] 保存 Phase 5 Kubernetes 驗收證據
- [x] 以 source-tree SHA-256 綁定本次驗收內容
- [ ] 正式版本發布前補充 Git commit SHA（非阻塞）

### Phase 6 — External AI Workload Compatibility Validation（Done）

子階段狀態：

- Phase 6.0 Compatibility Contract：Done
- Phase 6.1 External workload intake：Done
- Phase 6.2 Offline compatibility verification：Done（53/53 passed）
- Phase 6.3 Kubernetes E2E：Done
- Phase 6.4 CLI report acceptance：Done
- Phase 6.5 Completion and documentation release：Done

- [x] 建立 `docs/EXTERNAL_JOB_CONTRACT.md`
- [x] 定義 Core Safety、Workload Compatibility 與 GX10 environment 三層契約
- [x] 依使用者決策將門檻收斂為一個額外 external-model positive E2E
- [x] 選定 `unsloth/gemma-4-E2B-it-qat-w4a16` bounded generation case
- [x] 定義一個 external positive E2E、N1–N5 negative cases 與完成門檻
- [x] 建立 `docs/PHASE6_EXECUTION_PLAN.md`
- [x] 建立非 YOLO fixture 衍生的 Gemma 4 E2B Job 與 model provenance
- [x] 保存 source Job SHA-256
- [x] 實作欄位 preservation comparator
- [x] 完成 N1–N5 offline rejection verification
- [x] Gemma 4 E2B 完成七 CLI Kubernetes E2E
- [x] 驗證原始 YAML checksum 與 application semantics 保留
- [x] 驗證六項 artifacts、三方 checksum 與必要 Nsight summaries
- [x] report 由 `nsys stats` 從檔案成功解析，TXT/CSV 與五項必要
  summaries 完整
- [x] clean 後 Job/Pod 為零且本機 artifacts 保留
- [x] 完成 `evidence/phase-6/20260726-132018/acceptance.md`
- [ ] GUI timeline 與截圖（Deferred / Non-blocking）

## Blockers

| ID | 狀態 | 問題 | 解除條件 |
|---|---|---|---|
| B-001 | Resolved | GX10 Kubernetes context 與 API 存取曾不可用 | 已驗證 context `profile-job-builder@k3s`、namespace `profiling`、client/server `v1.35.4+k3s1`、node Ready，以及 Job/Pod/log/exec/Node 所需 RBAC |
| B-002 | Resolved | Nsight Systems 實際 host path 與版本未知 | 已確認 2025.3.2；掛載 root `/opt/nvidia/nsight-systems/2025.3.2`，target binary 位於 `target-linux-sbsa-armv8/nsys` |
| B-003 | Resolved | Scheduler probe 曾確認 PVC 不存在；管理者其後建立 `profiling/profile-artifacts` | PVC 已 Bound（20Gi、RWO、`local-path`），writer Pod 刪除後 readback Pod 成功讀回資料 |
| B-004 | Resolved | YOLO26 image tag 仍須解析為 immutable ARM64 digest | Registry manifest 已確認 Linux ARM64 digest `sha256:7db35781a755d11717f67b085f71b9b2ddee6c491c958e76e2526597a85b4757` |
| B-005 | Resolved / Contract Adjusted | Node allocatable 為 `nvidia.com/gpu.shared=4`，不提供 `nvidia.com/gpu` | 工程 smoke test 契約改用 `nvidia.com/gpu.shared: "1"`；正式獨占效能基準明確標記為目前不成立 |
| B-006 | Resolved / Contract Adjusted | YOLO26 Pod 僅請求 shared GPU 時 Torch 看不到 CUDA device | 加入 `runtimeClassName: nvidia` 後 Torch CUDA available、device count 1、device NVIDIA GB10；Target Spec 升至 v1.2，Builder 自動注入並拒絕衝突 RuntimeClass |
| B-007 | Deferred / Non-blocking | Workspace 不是 Git worktree，驗收未綁定 Git commit SHA | 本次功能驗收已綁定 source-tree SHA-256 `a95b470d8bbf9cea779da7aa70aa8dab12efd6abfe679009c25502ae9628b40a`；Git provenance 延後至正式版本管理或交付前補做，不阻塞 Phase 5 與 Phase 6 |

## Troubleshooting Log

| 日期 | Phase | 現象 | 根因 | 處置／結果 |
|---|---|---|---|---|
| 2026-07-24 | 0 | Workspace 無既有專案或 Git worktree | 初始目錄為空 | 從文檔契約建立專案基線；不把 Git 缺失視為功能驗收 |
| 2026-07-24 | 1 | `nsys profile` 無法建立 `/tmp/nvidia/nsight_systems` | 共用預設暫存路徑對執行 UID 不可寫 | preflight 與 Profile Job 使用執行專屬、可寫的 `TMPDIR` |
| 2026-07-24 | 1 | 沙箱內 `nvidia-smi` 顯示無法連接 driver | 沙箱未暴露 GPU device | 經核准在 host 執行後確認 NVIDIA GB10／driver 580.159.03 |
| 2026-07-24 | 1 | 工作區 shell 的 `kubectl` 曾嘗試連接 `localhost:8080` | 該執行環境未載入操作端 kubeconfig | 操作端其後完成 context/API/RBAC 驗證，B-001 已解除；cluster command 仍須在已載入該 context 的環境執行 |
| 2026-07-24 | 1 | `k3s.service` 不存在、`k3s-agent.service` 正常運行 | `gx10-c206` 是連到其他 control plane 的 worker | 需要由管理端提供 kubeconfig，不能使用本機 server config |
| 2026-07-24 | 1 | Agent 日誌曾出現 NVIDIA device plugin CrashLoop，後續註冊 `nvidia.com/gpu.shared` | Cluster 啟用了 GPU sharing | API 後續確認 shared=4 且 dedicated resource 不存在；已納入 v1.1 契約 |
| 2026-07-24 | 1 | `/etc/rancher/k3s/config.yaml.d` 顯示 permission denied warning | 非管理帳號無權讀取 K3s 設定片段，但 Kubernetes API、Node 查詢與 RBAC 均正常 | 警告可忽略；不修改 `/etc/rancher/k3s` 權限 |
| 2026-07-24 | 1/5 | RBAC 允許 `create jobs.batch`、Pod read/log、`create pods --subresource=exec`、`get nodes`，拒絕 `create pods` | Profile 專用 ServiceAccount 採最小權限；舊 `collect` helper Pod 設計不相容 | `collect` 改為對既有 collector container 執行 `exec`/`cp`，不再建立 helper Pod |
| 2026-07-24 | 1 | Node 只有 `nvidia.com/gpu.shared=4`，沒有 `nvidia.com/gpu` | Cluster device plugin 採 shared resource contract | B-005 結案並受控修訂 Target Spec v1.1；工程 smoke request 1 shared GPU，禁止獨占 benchmark 宣稱 |
| 2026-07-24 | 1 | 非特權 Pod hostPath smoke test | Job controller 建立 Pod；UID 65532 掛載 `/opt/nvidia/nsight-systems/2025.3.2` | Nsight 2025.3.2 成功執行，Pod Succeeded；Phase 1 完成 |
| 2026-07-24 | 2/4 | Reference Profile Job server-side dry-run 通過，但角色無 PVC get/create | RBAC 聚焦 Job/Pod 操作，storage 尚未交付 | Phase 2 可通過 API schema；實際提交前須解除 B-003 |
| 2026-07-24 | 4 | PVC probe Job 長時間 Pending | Scheduler 明確回報 `persistentvolumeclaim "profile-artifacts" not found` | 確認 PVC 不存在；Pod 未排程且未寫入資料，probe 已清理；B-003 需管理者處理 |
| 2026-07-24 | 4 | 管理者建立 PVC 後執行 writer/readback Jobs | `profile-artifacts` 已 Bound 至 local-path PV | writer 完成後刪除 Job；readback 仍讀回 timestamp，證明 Pod 刪除後持久性；B-003 Resolved |
| 2026-07-24 | 5 | `collect` 在 Pod 建立後立即執行時回報 `container not found ("profile-collector")` | Pod object 已存在，但 init containers 尚未完成，collector 尚未進入 Running | CLI 加入 collector Running 狀態等待，再執行 exec/cp |
| 2026-07-24 | 2/3/4/5 | YOLO26 Job 成功排程且 request shared GPU，但 Torch 看不到 CUDA device | Pod 未指定 GX10 的 `nvidia` RuntimeClass；需以最小 smoke test 驗證 | 保存 362,802-byte failure-path report 與 stats；B-006 Open，不將本次視為 CPU–GPU training 成功 |
| 2026-07-24 | 2/5 | `runtimeClassName: nvidia` visibility smoke | Torch 成功載入 NVIDIA container runtime 注入的 GB10 device | B-006 Resolved；受控修訂 Target Spec v1.2 與 Builder |
| 2026-07-24 | 4/5 | 刪除 Job 後以相同名稱重跑，collector 誤讀 PVC 中舊 report | deterministic Job name 對應相同持久化目錄，歷史 artifact 未隔離 | 停止重試並保留診斷目錄；init 現在拒絕任何非空 artifact 目錄，重跑必須使用唯一 `--name` |
| 2026-07-24 | 3 | GX10 shell 無法啟動 Nsight GUI | Session 為 TTY，無 DISPLAY/Wayland；OpenGL fallback 後仍缺 `libglapi.so.0` | 不冒充 GUI PASS；建立綁定 report checksum 的人工驗收表，改由有桌面的工作站開啟並保存截圖 |
| 2026-07-25 | 3 | 有桌面工作站完成 Nsight Systems 2025.3.2 人工驗收 | matching GUI 成功匯入 report，primary PID 96 具有 CUDA/NVTX/OS Runtime traces | Phase 3 判定 PASS with non-blocking limitations；timeline correlation 截圖仍建議補存，但不阻塞驗收 |
| 2026-07-25 | 5 | 嚴格執行三條 Kubernetes E2E 與七 CLI audit trail | 先前證據分散，且實作要求 `collect` acknowledgement 後 Job 才終止 | Success、application exit 7、collector stats failure 全部符合狀態契約；clean 後三個 Job 均 NotFound、Pods=0 |
| 2026-07-25 | 5 | 驗收未綁定 Git SHA | `/home/good_egg/profile-job-builder` 不是 Git worktree | 功能結果已綁定 source-tree SHA-256；B-007 降為 Deferred / Non-blocking，Phase 5 判定 Done |
| 2026-07-26 | 6 | preservation comparator 首次以 system Python 執行失敗 | system Python 未安裝 PyYAML | 改用專案 `.venv/bin/python` 重跑；20 項 preservation checks PASS，無 unexpected changes |
| 2026-07-26 | 6 | Gemma init dependency 安裝下載額外 Torch/CUDA packages | `pip --target` 未沿用 base image 的既有套件解析 | 本次 E2E 成功；列為非阻塞交付優化，正式使用建議改成 pinned ARM64 image |
| 2026-07-26 | 6 | 操作角色無法直接 `get` PVC | Profile Job RBAC 維持最小權限 | PVC 已由 Phase 4 證明 Bound/persistent，本次 Pod 實際 mount、write、collect 成功，不擴張權限 |
| 2026-07-26 | 6 | 新 shell 未明確指定 kubeconfig 時連線 `localhost:8080` | 驗收環境變數未跨 shell 繼承 | 最終狀態查詢以明確 `--kubeconfig`/`--context` 重跑並 PASS；失敗輸出保留，不影響 Job |
| 2026-07-26 | 6 | 原 Phase 6 gate 要求新 report 的 GUI 截圖 | 當前目標是技術驗證與檔案式自動解析，不是互動式人工分析 | GUI 降為 Deferred / Non-blocking；以 `nsys stats` 實際解析、必要 summaries、TXT/CSV、metadata 與 checksum 作為完成門檻 |

## Current Action Items

1. 正式版本交付前，將專案置於 Git worktree 並補充 commit provenance
   （非阻塞）。
2. 非阻塞選項：未來需要互動效能分析時，再以 GUI 開啟保存的
   `.nsys-rep`。

## Evidence Index

驗收證據將存放於 `evidence/phase-N/`。大型 `.nsys-rep` 不提交版本控制；索引只保存 checksum、metadata、stats、命令輸出與必要截圖路徑。

- `evidence/phase-1/node-preflight.txt`：host identity、Nsight、GPU、CUDA profile 及 stats。
- `evidence/phase-1/cuda-smoke/cuda-smoke.nsys-rep`：199,548 bytes，SHA-256 `6401f7d59df5f2c52cf199bf7eead964394702fad3823ddc169bda287527a7e8`。
- `evidence/phase-1/image-manifests.md`：YOLO26 與 Ubuntu ARM64 immutable manifests。
- `evidence/phase-1/kubernetes-access-rbac.md`：操作端 Kubernetes context、Node、RBAC 與 GPU resource 驗證紀錄。
- `evidence/phase-1/kubernetes-hostpath-smoke.txt`：非特權 Pod hostPath mount、Nsight version 與完成狀態。
- `evidence/phase-2/server-dry-run.txt`：手寫與 Builder 產生之 Profile Job 的 API server dry-run。
- `evidence/phase-2/yolo26-attempt-1.md`：第一次 cluster run、GPU visibility 失敗與 failure-path artifact 證據。
- `evidence/phase-2/shared-gpu-runtimeclass-smoke.txt`：NVIDIA RuntimeClass 下 Torch/GB10 visibility 證據。
- `evidence/phase-2/yolo26-success.md`：YOLO26 GPU training、Job Complete、report checksum 與 CUDA summaries。
- `evidence/phase-3/gui-acceptance.md`：GUI PASS、指定 report/checksum、
  session facts、已知限制與建議補強截圖。
- `evidence/phase-4/pvc-probe.txt`：Scheduler 確認 PVC 不存在的 probe 狀態與清理紀錄。
- `evidence/phase-4/pvc-persistence-success.txt`：PVC Bound、writer/readback 與 Pod 刪除後持久性證據。
- `evidence/phase-4/failure-matrix.md`：完整 failure classification、真實 Nsight exit-0/error 陷阱、Kubernetes failure/success regression。
- `evidence/phase-5/tests.txt`：45 個通過的離線 tests。
- `evidence/phase-5/yolo26-transform.diff`：YOLO26 source Job 到 Profile Job 的人工審查 diff。
- `evidence/phase-5/20260725-124855/cluster-integration.md`：三條真實
  Kubernetes E2E、七 CLI transcripts、metadata/artifact/checksum 與 clean
  驗證；PASS，並以 source-tree SHA-256 綁定。
- `docs/EXTERNAL_JOB_CONTRACT.md`：Phase 6A external provenance、相容性
  邊界、欄位 preservation 與 completion gate。
- `docs/PHASE6_EXECUTION_PLAN.md`：Phase 6 分階段執行、證據結構、比較器與
  E2E/GUI 驗收程序。
- `evidence/phase-6/20260726-132018/acceptance.md`：Gemma 4 E2B 七 CLI、
  Kubernetes E2E、field preservation、negative cases、artifacts、
  checksum、CLI structured summaries 與 clean 證據；Phase 6 PASS。
