#!/usr/bin/env bash

set -uo pipefail

EXPECTED_NODE="gx10-c206"
NSYS_ROOT=""
CUDA_COMMAND=""
SMOKE_OUTPUT=""
SKIP_KUBERNETES=false

usage() {
  printf '%s\n' \
    "Usage: scripts/node-preflight.sh [options]" \
    "" \
    "Options:" \
    "  --expected-node NAME    Expected hostname (default: gx10-c206)" \
    "  --nsys-root PATH        Nsight Systems target runtime directory" \
    "  --cuda-command COMMAND  Optional shell command used for the host CUDA smoke test" \
    "  --smoke-output DIR      Keep CUDA smoke-test artifacts in this new/empty directory" \
    "  --skip-kubernetes       Skip API and RBAC checks when no kubeconfig is available" \
    "  --help                  Show this help"
}

while (($# > 0)); do
  case "$1" in
    --expected-node)
      EXPECTED_NODE="${2:?--expected-node requires a value}"
      shift 2
      ;;
    --nsys-root)
      NSYS_ROOT="${2:?--nsys-root requires a value}"
      shift 2
      ;;
    --cuda-command)
      CUDA_COMMAND="${2:?--cuda-command requires a value}"
      shift 2
      ;;
    --smoke-output)
      SMOKE_OUTPUT="${2:?--smoke-output requires a value}"
      shift 2
      ;;
    --skip-kubernetes)
      SKIP_KUBERNETES=true
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
  printf 'PASS  %s\n' "$1"
}

fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  printf 'FAIL  %s\n' "$1"
}

warn() {
  WARN_COUNT=$((WARN_COUNT + 1))
  printf 'WARN  %s\n' "$1"
}

section() {
  printf '\n[%s]\n' "$1"
}

run_and_report() {
  local label="$1"
  shift
  printf '$'
  printf ' %q' "$@"
  printf '\n'
  if "$@" 2>&1; then
    pass "$label"
  else
    fail "$label"
  fi
}

discover_nsys_root() {
  local candidate
  while IFS= read -r candidate; do
    if [[ -x "$candidate/nsys" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done < <(
    find /opt/nvidia/nsight-systems \
      -mindepth 2 -maxdepth 2 \
      -type d -name 'target-linux-sbsa-armv8' \
      2>/dev/null | sort -V -r
  )
  return 1
}

section "identity"
printf 'timestamp_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf 'hostname=%s\n' "$(hostname)"
printf 'architecture=%s\n' "$(uname -m)"
printf 'kernel=%s\n' "$(uname -r)"

if [[ "$(hostname)" == "$EXPECTED_NODE" ]]; then
  pass "hostname is $EXPECTED_NODE"
else
  fail "hostname is not $EXPECTED_NODE"
fi

if [[ "$(uname -m)" == "aarch64" ]]; then
  pass "architecture is aarch64"
else
  fail "architecture is not aarch64"
fi

section "nsight-systems"
if command -v nsys >/dev/null 2>&1; then
  run_and_report "nsys CLI is executable" nsys --version
  printf 'nsys_launcher=%s\n' "$(command -v nsys)"
else
  fail "nsys CLI is not on PATH"
fi

if [[ -z "$NSYS_ROOT" ]]; then
  NSYS_ROOT="$(discover_nsys_root || true)"
fi

if [[ -n "$NSYS_ROOT" ]]; then
  printf 'nsys_target_root=%s\n' "$NSYS_ROOT"
  if [[ "$NSYS_ROOT" == /* && -d "$NSYS_ROOT" ]]; then
    pass "Nsight target root is an absolute directory"
  else
    fail "Nsight target root is not an absolute directory"
  fi
  if [[ -x "$NSYS_ROOT/nsys" ]]; then
    run_and_report "mounted target nsys is executable" "$NSYS_ROOT/nsys" --version
  else
    fail "$NSYS_ROOT/nsys is not executable"
  fi
  if find "$NSYS_ROOT" -type f ! -readable -print -quit 2>/dev/null | grep -q .; then
    fail "Nsight target root contains files unreadable by uid $(id -u)"
  else
    pass "Nsight target root files are readable by uid $(id -u)"
  fi
else
  fail "unable to discover Nsight target root"
fi

printf '$ nsys status --environment\n'
STATUS_OUTPUT="$(nsys status --environment 2>&1)"
STATUS_CODE=$?
printf '%s\n' "$STATUS_OUTPUT"
if grep -q 'CPU Profiling Environment.*Fail' <<<"$STATUS_OUTPUT"; then
  warn "CPU sampling is unavailable; Phase 1 requires --sample=none"
elif ((STATUS_CODE == 0)); then
  pass "Nsight environment status command completed"
else
  fail "Nsight environment status command failed"
fi

section "gpu"
if command -v nvidia-smi >/dev/null 2>&1; then
  run_and_report \
    "NVIDIA driver and GPU are visible" \
    nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
else
  fail "nvidia-smi is not installed"
fi

section "kubernetes"
if [[ "$SKIP_KUBERNETES" == true ]]; then
  warn "Kubernetes checks skipped by request"
elif command -v kubectl >/dev/null 2>&1; then
  run_and_report "kubectl client is available" kubectl version --client
  CURRENT_CONTEXT="$(kubectl config current-context 2>/dev/null || true)"
  printf 'current_context=%s\n' "${CURRENT_CONTEXT:-<none>}"
  if [[ "$CURRENT_CONTEXT" == "profile-job-builder@k3s" ]]; then
    pass "current context is profile-job-builder@k3s"
  else
    fail "current context is not profile-job-builder@k3s"
  fi
  run_and_report "Kubernetes client and server versions are readable" kubectl version
  run_and_report "Kubernetes API is reachable" kubectl get node "$EXPECTED_NODE" -o name
  DEDICATED_GPU="$(
    kubectl get node "$EXPECTED_NODE" \
      -o 'jsonpath={.status.allocatable.nvidia\.com/gpu}' 2>/dev/null || true
  )"
  SHARED_GPU="$(
    kubectl get node "$EXPECTED_NODE" \
      -o 'jsonpath={.status.allocatable.nvidia\.com/gpu\.shared}' 2>/dev/null || true
  )"
  printf 'allocatable_nvidia_com_gpu=%s\n' "${DEDICATED_GPU:-<none>}"
  printf 'allocatable_nvidia_com_gpu_shared=%s\n' "${SHARED_GPU:-<none>}"
  if [[ "$DEDICATED_GPU" =~ ^[1-9][0-9]*$ ]]; then
    pass "node advertises dedicated nvidia.com/gpu"
  else
    warn "node does not advertise dedicated nvidia.com/gpu; exclusive benchmark is unavailable"
  fi
  if [[ "$SHARED_GPU" =~ ^[1-9][0-9]*$ ]]; then
    pass "node advertises nvidia.com/gpu.shared for the engineering smoke test"
  elif [[ ! "$DEDICATED_GPU" =~ ^[1-9][0-9]*$ ]]; then
    fail "node advertises neither a shared nor dedicated NVIDIA GPU resource"
  fi
  run_and_report "caller may create Jobs" kubectl auth can-i create jobs.batch
  run_and_report "caller may read Pods" kubectl auth can-i get pods
  run_and_report \
    "caller may read Pod logs" \
    kubectl auth can-i get pods --subresource=log
  run_and_report \
    "caller may exec in Pods" \
    kubectl auth can-i create pods --subresource=exec
  run_and_report "caller may read Nodes" kubectl auth can-i get nodes
else
  fail "kubectl is not installed"
fi

section "cuda-smoke-test"
if [[ -z "$CUDA_COMMAND" ]]; then
  warn "host CUDA smoke test skipped; pass --cuda-command"
elif [[ -z "$NSYS_ROOT" || ! -x "$NSYS_ROOT/nsys" ]]; then
  fail "host CUDA smoke test cannot run without target nsys"
else
  if [[ -n "$SMOKE_OUTPUT" ]]; then
    if [[ "$SMOKE_OUTPUT" != /* ]]; then
      fail "--smoke-output must be an absolute path"
      SMOKE_DIR="$(mktemp -d)"
    elif [[ -d "$SMOKE_OUTPUT" && -n "$(find "$SMOKE_OUTPUT" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
      fail "--smoke-output must be new or empty"
      SMOKE_DIR="$(mktemp -d)"
    else
      mkdir -p "$SMOKE_OUTPUT"
      SMOKE_DIR="$SMOKE_OUTPUT"
    fi
  else
    SMOKE_DIR="$(mktemp -d)"
  fi
  REPORT_BASE="$SMOKE_DIR/cuda-smoke"
  printf 'temporary_output=%s\n' "$SMOKE_DIR"
  printf '$ %q profile --trace=cuda,nvtx,osrt --sample=none --cpuctxsw=none --force-overwrite=true --output=%q bash -lc %q\n' \
    "$NSYS_ROOT/nsys" "$REPORT_BASE" "$CUDA_COMMAND"
  TMPDIR="$SMOKE_DIR" "$NSYS_ROOT/nsys" profile \
    --trace=cuda,nvtx,osrt \
    --sample=none \
    --cpuctxsw=none \
    --force-overwrite=true \
    --output="$REPORT_BASE" \
    bash -lc "$CUDA_COMMAND"
  SMOKE_CODE=$?
  if ((SMOKE_CODE == 0)) && [[ -s "$REPORT_BASE.nsys-rep" ]]; then
    pass "host CUDA profile produced a non-empty report"
    run_and_report "host CUDA report is parseable" \
      "$NSYS_ROOT/nsys" stats "$REPORT_BASE.nsys-rep"
  else
    fail "host CUDA profile did not produce a non-empty report"
  fi
  printf 'smoke_report=%s\n' "$REPORT_BASE.nsys-rep"
fi

section "summary"
printf 'pass=%d\nfail=%d\nwarn=%d\n' "$PASS_COUNT" "$FAIL_COUNT" "$WARN_COUNT"

if ((FAIL_COUNT > 0)); then
  exit 1
fi
