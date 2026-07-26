from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from .errors import InputError
from .validation import ValidatedJob, validate_source_job

PROFILE_LABEL = "profile-job-builder.local/enabled"
SOURCE_ANNOTATION = "profile-job-builder.local/source-job"
VERSION_ANNOTATION = "profile-job-builder.local/spec-version"
ORIGINAL_COMMAND_ANNOTATION = "profile-job-builder.local/original-command"
HOSTNAME_LABEL = "kubernetes.io/hostname"

NSYS_MOUNT = "/opt/profiler/nsys"
OUTPUT_MOUNT = "/profile-output"
NSYS_BINARY = f"{NSYS_MOUNT}/target-linux-sbsa-armv8/nsys"
UBUNTU_ARM64_IMAGE = (
    "ubuntu:24.04@sha256:7f622ca8766bccb22f04242ecb6f19f770b2f08827dc4b8c707de5e78a6da7ab"
)


@dataclass(frozen=True)
class BuildConfig:
    target_container: str | None = None
    node: str = "gx10-c206"
    runtime_class_name: str = "nvidia"
    name: str | None = None
    nsys_host_path: str = "/opt/nvidia/nsight-systems/2025.3.2"
    artifact_pvc: str | None = "profile-artifacts"
    collector_image: str = UBUNTU_ARM64_IMAGE
    init_image: str = UBUNTU_ARM64_IMAGE
    collector_timeout_seconds: int = 3600
    include_collector: bool = True
    entrypoint: str | None = None
    args: tuple[str, ...] = ()


def _dns_name(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    if not normalized:
        raise InputError("cannot derive a DNS-compatible Profile Job name")
    if len(normalized) <= 63:
        return normalized
    digest = hashlib.sha256(normalized.encode()).hexdigest()[:8]
    return f"{normalized[:54].rstrip('-')}-{digest}"


def _profile_name(source_name: str, requested: str | None) -> str:
    return _dns_name(requested or f"{source_name}-profile")


def _clean_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        raise InputError("metadata must be a mapping")
    cleaned = copy.deepcopy(metadata)
    for key in (
        "creationTimestamp",
        "deletionGracePeriodSeconds",
        "deletionTimestamp",
        "finalizers",
        "generateName",
        "generation",
        "managedFields",
        "ownerReferences",
        "resourceVersion",
        "selfLink",
        "uid",
    ):
        cleaned.pop(key, None)
    annotations = cleaned.get("annotations")
    if isinstance(annotations, dict):
        annotations.pop("kubectl.kubernetes.io/last-applied-configuration", None)
        if not annotations:
            cleaned.pop("annotations", None)
    return cleaned


def _upsert_env(container: dict[str, Any], name: str, value: str) -> None:
    env = container.setdefault("env", [])
    if not isinstance(env, list):
        raise InputError(f"container env must be a list, got {type(env).__name__}")
    env[:] = [
        item
        for item in env
        if not (isinstance(item, dict) and item.get("name") == name)
    ]
    env.append({"name": name, "value": value})


def _collector_script(output_dir: str, timeout: int) -> str:
    required_reports = (
        "osrt_sum cuda_api_sum cuda_gpu_kern_sum "
        "cuda_gpu_mem_time_sum cuda_gpu_mem_size_sum"
    )
    return f"""\
report={output_dir}/profile.nsys-rep
application_finished={output_dir}/.application-finished
expected_checksum_file={output_dir}/.expected-sha256
ready={output_dir}/.collector-ready
ack={output_dir}/.collected
metadata={output_dir}/profile-metadata.json
stats_stderr={output_dir}/nsys-stats.stderr.txt
nsys_binary="${{NSYS_BINARY_OVERRIDE:-{NSYS_BINARY}}}"
required_reports="${{PROFILE_REQUIRED_REPORTS:-{required_reports}}}"
report_exists=false
report_size_bytes=0
report_valid=false
stats_complete=false
expected_checksum=
actual_checksum=
checksum_match=false
application_exit_code=

write_metadata() {{
  overall_status=$1
  failure_reason=$2
  collector_exit_code=$3
  nsys_version=$("$nsys_binary" --version 2>/dev/null | head -n 1 | tr '"' "'" || true)
  finished_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  printf '{{"status":"%s","overall_status":"%s","failure_reason":"%s","application_exit_code":%s,"report_exists":%s,"report_size_bytes":%s,"report_valid":%s,"expected_checksum":"%s","actual_checksum":"%s","checksum_match":%s,"stats_complete":%s,"collector_exit_code":%s,"nsys_version":"%s","finished_at":"%s"}}\\n' \
    "$overall_status" "$overall_status" "$failure_reason" \
    "${{application_exit_code:-null}}" "$report_exists" "$report_size_bytes" \
    "$report_valid" "$expected_checksum" "$actual_checksum" "$checksum_match" \
    "$stats_complete" "$collector_exit_code" "$nsys_version" "$finished_at" \
    > "$metadata"
}}

await_collection_ack() {{
  result=$1
  touch "$ready"
  collection_deadline=$(( $(date +%s) + {timeout} ))
  while [ ! -f "$ack" ]; do
    if [ "$(date +%s)" -ge "$collection_deadline" ]; then
      failure_reason=collection_ack_timeout
      write_metadata failed "$failure_reason" 125
      exit 125
    fi
    sleep 2
  done
  exit "$result"
}}

fail_collection() {{
  failure_reason=$1
  collector_exit_code=$2
  write_metadata failed "$failure_reason" "$collector_exit_code"
  await_collection_ack "$collector_exit_code"
}}

deadline=$(( $(date +%s) + {timeout} ))
while [ ! -f "$application_finished" ]; do
  if [ "$(date +%s)" -ge "$deadline" ]; then
    fail_collection application_timeout 124
  fi
  sleep 2
done

application_exit_code=$(cat "$application_finished")
case "$application_exit_code" in
  ''|*[!0-9]*) fail_collection invalid_application_exit_code 126 ;;
esac

if [ ! -e "$report" ]; then
  fail_collection missing_report 20
fi
report_exists=true
report_size_bytes=$(wc -c < "$report")
if [ "$report_size_bytes" -eq 0 ]; then
  fail_collection empty_report 21
fi

if [ ! -s "$expected_checksum_file" ]; then
  fail_collection expected_checksum_missing 22
fi
expected_checksum=$(cat "$expected_checksum_file")
set -- $(sha256sum "$report")
actual_checksum=$1
if [ "$expected_checksum" != "$actual_checksum" ]; then
  fail_collection integrity_failure 23
fi
checksum_match=true

mkdir -p {output_dir}/tmp-collector
export TMPDIR={output_dir}/tmp-collector
parts={output_dir}/stats-parts
mkdir -p "$parts"
: > "$stats_stderr"

run_stats() {{
  stats_report_name=$1
  stats_format=$2
  stats_output=$3
  stats_error="$stats_output.stderr"
  if [ "$stats_format" = csv ]; then
    "$nsys_binary" stats --force-export=true --format=csv \
      --report="$stats_report_name" "$report" \
      > "$stats_output" 2> "$stats_error"
    stats_exit=$?
  else
    "$nsys_binary" stats --force-export=true --report="$stats_report_name" "$report" \
      > "$stats_output" 2> "$stats_error"
    stats_exit=$?
  fi
  cat "$stats_error" >> "$stats_stderr"
  if [ "$stats_exit" -ne 0 ] || [ ! -s "$stats_output" ]; then
    return 1
  fi
  if grep -Eiq 'Exportation error:|ERROR:' "$stats_output" "$stats_error"; then
    printf 'nsys stats emitted an error despite exit code %s:\\n' "$stats_exit" \
      >> "$stats_stderr"
    cat "$stats_output" >> "$stats_stderr"
    return 1
  fi
  return 0
}}

if ! run_stats osrt_sum text "$parts/report-validation.txt"; then
  header=$(head -c 28 "$report" || true)
  case "$header" in
    "NVIDIA Tegra Profiler Report"*) fail_collection corrupted_report 24 ;;
    *) fail_collection parse_failure 25 ;;
  esac
fi
report_valid=true

required_reports_csv=$(printf '%s' "$required_reports" | tr ' ' ',')
all_reports="$required_reports_csv,nvtx_sum"
stats_text_candidate="$parts/nsys-stats.txt.partial"
stats_csv_candidate="$parts/nsys-stats.csv.partial"
if ! run_stats "$all_reports" text "$stats_text_candidate"; then
  fail_collection stats_failure 26
fi
if ! run_stats "$all_reports" csv "$stats_csv_candidate"; then
  fail_collection stats_failure 26
fi

for summary in \
  'OS Runtime Summary' \
  'CUDA API Summary' \
  'CUDA GPU Kernel Summary' \
  'CUDA GPU MemOps Summary (by Time)' \
  'CUDA GPU MemOps Summary (by Size)'; do
  if ! grep -Fq "$summary" "$stats_text_candidate"; then
    printf 'required summary missing: %s\\n' "$summary" >> "$stats_stderr"
    fail_collection stats_failure 26
  fi
done

mv "$stats_text_candidate" {output_dir}/nsys-stats.txt
mv "$stats_csv_candidate" {output_dir}/nsys-stats.csv
stats_complete=true
if [ "$application_exit_code" -ne 0 ]; then
  fail_collection application_exit_nonzero 27
fi
write_metadata success none 0
await_collection_ack 0
"""


def _application_script(output_dir: str) -> str:
    return f"""\
report={output_dir}/profile.nsys-rep
set +e
{NSYS_BINARY} profile \
  --trace=cuda,nvtx,osrt \
  --sample=none \
  --cpuctxsw=none \
  --force-overwrite=true \
  --output={output_dir}/profile \
  "$@"
application_exit_code=$?
set -e
if [ -e "$report" ]; then
  set -- $(sha256sum "$report")
  printf '%s\\n' "$1" > {output_dir}/.expected-sha256
fi
printf '%s\\n' "$application_exit_code" > {output_dir}/.application-finished
exit "$application_exit_code"
"""


def build_profile_job(source: dict[str, Any], config: BuildConfig) -> dict[str, Any]:
    if config.collector_timeout_seconds < 30:
        raise InputError("collector timeout must be at least 30 seconds")
    if not config.nsys_host_path.startswith("/"):
        raise InputError("Nsight host path must be absolute")
    if config.include_collector and not config.artifact_pvc:
        raise InputError("collector builds require --artifact-pvc for persistent artifacts")

    validated: ValidatedJob = validate_source_job(
        source,
        config.target_container,
        config.entrypoint,
        list(config.args),
    )
    result = copy.deepcopy(source)
    source_name = str(source["metadata"]["name"])
    name = _profile_name(source_name, config.name)
    output_dir = f"{OUTPUT_MOUNT}/{name}"

    result.pop("status", None)
    metadata = _clean_metadata(result["metadata"])
    metadata["name"] = name
    labels = metadata.setdefault("labels", {})
    if not isinstance(labels, dict):
        raise InputError("metadata.labels must be a mapping")
    labels[PROFILE_LABEL] = "true"
    annotations = metadata.setdefault("annotations", {})
    annotations[SOURCE_ANNOTATION] = source_name
    annotations[VERSION_ANNOTATION] = "v1.2"
    annotations[ORIGINAL_COMMAND_ANNOTATION] = json.dumps(
        [*validated.command, *validated.args],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    result["metadata"] = metadata

    job_spec = result["spec"]
    for key in (
        "completionMode",
        "manualSelector",
        "selector",
        "suspend",
        "ttlSecondsAfterFinished",
    ):
        job_spec.pop(key, None)
    job_spec["parallelism"] = 1
    job_spec["completions"] = 1
    job_spec["backoffLimit"] = 0

    template = job_spec["template"]
    template_metadata = _clean_metadata(template.get("metadata") or {})
    template_labels = template_metadata.setdefault("labels", {})
    if not isinstance(template_labels, dict):
        raise InputError("spec.template.metadata.labels must be a mapping")
    template_labels[PROFILE_LABEL] = "true"
    template["metadata"] = template_metadata
    pod_spec = template["spec"]
    pod_spec["restartPolicy"] = "Never"
    existing_runtime_class = pod_spec.get("runtimeClassName")
    if existing_runtime_class not in (None, config.runtime_class_name):
        raise InputError(
            f"source Job uses runtimeClassName {existing_runtime_class!r}; "
            f"GX10 profiling requires {config.runtime_class_name!r}"
        )
    pod_spec["runtimeClassName"] = config.runtime_class_name
    node_selector = pod_spec.setdefault("nodeSelector", {})
    existing_node = node_selector.get(HOSTNAME_LABEL)
    if existing_node not in (None, config.node):
        raise InputError(
            f"source Job targets node {existing_node!r}; refusing to replace it with {config.node!r}"
        )
    node_selector[HOSTNAME_LABEL] = config.node

    volumes = pod_spec.setdefault("volumes", [])
    volumes.append(
        {
            "name": "nsys-runtime",
            "hostPath": {"path": config.nsys_host_path, "type": "Directory"},
        }
    )
    if config.artifact_pvc:
        volumes.append(
            {
                "name": "profile-output",
                "persistentVolumeClaim": {"claimName": config.artifact_pvc},
            }
        )
    else:
        volumes.append({"name": "profile-output", "emptyDir": {}})

    init_containers = pod_spec.setdefault("initContainers", [])
    init_containers.append(
        {
            "name": "profile-output-init",
            "image": config.init_image,
            "command": ["/bin/sh", "-ceu"],
            "args": [
                f"if [ -d {output_dir} ] && "
                f'[ -n "$(find {output_dir} -mindepth 1 -maxdepth 1 '
                f'-print -quit)" ]; then '
                f"printf 'refusing to reuse non-empty artifact directory: "
                f"{output_dir}\\n' >&2; exit 73; fi; "
                f"mkdir -p {output_dir} && chmod 0777 {output_dir}"
            ],
            "resources": {
                "requests": {"cpu": "5m", "memory": "8Mi"},
                "limits": {"cpu": "100m", "memory": "32Mi"},
            },
            "volumeMounts": [{"name": "profile-output", "mountPath": OUTPUT_MOUNT}],
            "securityContext": {
                "allowPrivilegeEscalation": False,
                "capabilities": {"drop": ["ALL"]},
            },
        }
    )

    app = pod_spec["containers"][0]
    original_command = validated.command
    original_args = validated.args
    app["command"] = ["/bin/sh", "-ceu"]
    app["args"] = [
        _application_script(output_dir),
        "--",
        *original_command,
        *original_args,
    ]
    mounts = app.setdefault("volumeMounts", [])
    mounts.extend(
        [
            {"name": "nsys-runtime", "mountPath": NSYS_MOUNT, "readOnly": True},
            {"name": "profile-output", "mountPath": OUTPUT_MOUNT},
        ]
    )
    _upsert_env(app, "TMPDIR", output_dir)
    _upsert_env(app, "PROFILE_OUTPUT_DIR", output_dir)

    if config.include_collector:
        collector = {
            "name": "profile-collector",
            "image": config.collector_image,
            "command": ["/bin/sh", "-ceu"],
            "args": [_collector_script(output_dir, config.collector_timeout_seconds)],
            "env": [{"name": "PROFILE_JOB_NAME", "value": name}],
            "resources": {
                "requests": {"cpu": "50m", "memory": "128Mi"},
                "limits": {"cpu": "1", "memory": "1Gi"},
            },
            "volumeMounts": [
                {"name": "nsys-runtime", "mountPath": NSYS_MOUNT, "readOnly": True},
                {"name": "profile-output", "mountPath": OUTPUT_MOUNT},
            ],
            "securityContext": {
                "allowPrivilegeEscalation": False,
                "capabilities": {"drop": ["ALL"]},
            },
        }
        pod_spec["containers"].append(collector)

    return result


def inspect_job(source: dict[str, Any], target_container: str | None) -> dict[str, Any]:
    validated = validate_source_job(source, target_container)
    resources = validated.container.get("resources", {})
    return {
        "apiVersion": source.get("apiVersion"),
        "kind": source.get("kind"),
        "name": source["metadata"]["name"],
        "namespace": source["metadata"].get("namespace", "default"),
        "targetContainer": validated.target_container,
        "image": validated.container.get("image"),
        "command": validated.command,
        "args": validated.args,
        "gpuResource": validated.gpu_resource,
        "gpuMode": (
            "shared"
            if validated.gpu_resource == "nvidia.com/gpu.shared"
            else "dedicated"
        ),
        "gpuLimits": resources.get("limits", {}).get(validated.gpu_resource),
        "gpuRequests": resources.get("requests", {}).get(validated.gpu_resource),
        "volumes": [
            item.get("name")
            for item in validated.pod_spec.get("volumes", [])
            if isinstance(item, dict)
        ],
    }
