# GX10 Kubernetes access and RBAC evidence

> 日期：2026-07-24  
> 證據來源：GX10 操作端驗證紀錄，並已由本工作區使用
> `/home/good_egg/.kube/profile-job-builder.kubeconfig` 重播確認。

## 已確認

- Current context：`profile-job-builder@k3s`
- Authorized workload namespace：`profiling`
- Kubernetes client：`v1.35.4+k3s1`
- Kubernetes server：`v1.35.4+k3s1`
- Node `gx10-c206`：`Ready`
- Allocatable GPU：
  - `nvidia.com/gpu.shared=4`
  - `nvidia.com/gpu` 不存在

## RBAC

允許：

- `create jobs.batch`
- `get pods`
- `get pods/log`
- `create pods --subresource=exec`
- `get nodes`

拒絕：

- `create pods`
- `get secrets`
- `delete nodes`

額外確認：

- `list/watch pods`：允許
- `delete jobs.batch`：允許
- `get/create persistentvolumeclaims`：拒絕（B-003）

因此 Profile Job 可由 `jobs.batch` 建立；artifact collection 必須使用既有
Profile Pod 的 logs/exec，不能建立 helper Pod。

上述 namespaced 權限只適用於 `profiling`；`default` namespace 無
Job/Pod/PVC 權限。Reference YAML 因此明確指定 `metadata.namespace:
profiling`。

## 決策

- 工程 smoke test 使用 `nvidia.com/gpu.shared: "1"`。
- shared GPU 結果不得宣稱為獨占 GPU 效能基準。
- `WARN open /etc/rancher/k3s/config.yaml.d: permission denied` 在 API、Node
  與 RBAC 查詢成功時可忽略。
- 不修改 `/etc/rancher/k3s` 權限。
