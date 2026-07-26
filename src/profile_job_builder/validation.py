from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .errors import InputError

GPU_RESOURCES = ("nvidia.com/gpu.shared", "nvidia.com/gpu")
RESERVED_CONTAINERS = {"profile-collector", "profile-output-init"}
RESERVED_VOLUMES = {"profile-output", "nsys-runtime"}
RESERVED_MOUNT_PATHS = {"/profile-output", "/opt/profiler/nsys"}


@dataclass(frozen=True)
class ValidatedJob:
    job: dict[str, Any]
    pod_spec: dict[str, Any]
    container: dict[str, Any]
    target_container: str
    command: list[str]
    args: list[str]
    gpu_resource: str


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _gpu_value(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed


def _has_sys_ptrace(security_context: Any) -> bool:
    if not isinstance(security_context, dict):
        return False
    capabilities = security_context.get("capabilities")
    if not isinstance(capabilities, dict):
        return False
    return any(str(item).upper() == "SYS_PTRACE" for item in _as_list(capabilities.get("add")))


def validate_source_job(
    job: dict[str, Any],
    target_container: str | None,
    entrypoint: str | None = None,
    override_args: list[str] | None = None,
) -> ValidatedJob:
    errors: list[str] = []

    if job.get("apiVersion") != "batch/v1":
        errors.append("apiVersion must be batch/v1")
    if job.get("kind") != "Job":
        errors.append("kind must be Job")

    metadata = job.get("metadata")
    if not isinstance(metadata, dict) or not metadata.get("name"):
        errors.append("metadata.name is required")

    job_spec = job.get("spec")
    if not isinstance(job_spec, dict):
        errors.append("spec must be a mapping")
        job_spec = {}
    template = job_spec.get("template")
    if not isinstance(template, dict):
        errors.append("spec.template must be a mapping")
        template = {}
    pod_spec = template.get("spec")
    if not isinstance(pod_spec, dict):
        errors.append("spec.template.spec must be a mapping")
        pod_spec = {}

    if pod_spec.get("hostPID") is True:
        errors.append("hostPID is forbidden")
    if pod_spec.get("shareProcessNamespace") is True:
        errors.append("shareProcessNamespace is forbidden")

    containers = _as_list(pod_spec.get("containers"))
    if len(containers) != 1:
        errors.append(
            f"exactly one application container is supported; found {len(containers)}"
        )

    container: dict[str, Any] = containers[0] if len(containers) == 1 and isinstance(containers[0], dict) else {}
    actual_name = str(container.get("name", ""))
    selected_name = target_container or actual_name
    if not selected_name:
        errors.append("target container name is required")
    elif actual_name and selected_name != actual_name:
        errors.append(
            f"target container {selected_name!r} does not match the only container {actual_name!r}"
        )
    if actual_name in RESERVED_CONTAINERS:
        errors.append(f"container name {actual_name!r} is reserved")

    init_containers = _as_list(pod_spec.get("initContainers"))
    init_names = {
        str(item.get("name"))
        for item in init_containers
        if isinstance(item, dict) and item.get("name") is not None
    }
    init_conflicts = sorted(init_names & RESERVED_CONTAINERS)
    if init_conflicts:
        errors.append(f"reserved init container name conflict: {', '.join(init_conflicts)}")
    if _as_list(pod_spec.get("ephemeralContainers")):
        errors.append("ephemeralContainers are not supported")

    security_contexts = [
        pod_spec.get("securityContext"),
        container.get("securityContext"),
        *[
            item.get("securityContext")
            for item in init_containers
            if isinstance(item, dict)
        ],
    ]
    if any(isinstance(item, dict) and item.get("privileged") is True for item in security_contexts):
        errors.append("privileged securityContext is forbidden")
    if any(_has_sys_ptrace(item) for item in security_contexts):
        errors.append("SYS_PTRACE capability is forbidden")

    volumes = _as_list(pod_spec.get("volumes"))
    volume_names = {
        str(item.get("name"))
        for item in volumes
        if isinstance(item, dict) and item.get("name") is not None
    }
    conflicts = sorted(volume_names & RESERVED_VOLUMES)
    if conflicts:
        errors.append(f"reserved volume name conflict: {', '.join(conflicts)}")

    mount_paths: set[str] = set()
    for candidate in [container, *init_containers]:
        if not isinstance(candidate, dict):
            continue
        mount_paths.update(
            str(item.get("mountPath"))
            for item in _as_list(candidate.get("volumeMounts"))
            if isinstance(item, dict) and item.get("mountPath") is not None
        )
    mount_conflicts = sorted(mount_paths & RESERVED_MOUNT_PATHS)
    if mount_conflicts:
        errors.append(f"reserved mount path conflict: {', '.join(mount_conflicts)}")

    resources = container.get("resources")
    resources = resources if isinstance(resources, dict) else {}
    limits = resources.get("limits")
    limits = limits if isinstance(limits, dict) else {}
    requests = resources.get("requests")
    requests = requests if isinstance(requests, dict) else {}
    configured_gpu_resources = [
        resource for resource in GPU_RESOURCES if resource in limits
    ]
    if len(configured_gpu_resources) != 1:
        errors.append(
            "application container must set exactly one supported GPU limit "
            "(nvidia.com/gpu.shared or nvidia.com/gpu)"
        )
        gpu_resource = ""
    else:
        gpu_resource = configured_gpu_resources[0]
        if _gpu_value(limits.get(gpu_resource)) != 1:
            errors.append(f"limits.{gpu_resource} must be exactly 1")
        gpu_request = (
            _gpu_value(requests.get(gpu_resource))
            if gpu_resource in requests
            else None
        )
        if gpu_request not in (None, 1):
            errors.append(f"requests.{gpu_resource} must be omitted or exactly 1")
        other_resource = next(
            resource for resource in GPU_RESOURCES if resource != gpu_resource
        )
        if other_resource in requests:
            errors.append(
                f"requests.{other_resource} cannot be combined with limits.{gpu_resource}"
            )

    command = _as_list(container.get("command"))
    args = _as_list(container.get("args"))
    if entrypoint is not None:
        command = [entrypoint]
        args = list(override_args or [])
    elif override_args:
        errors.append("--arg requires --entrypoint")
    if not command or not all(isinstance(item, str) and item for item in command):
        errors.append("a non-empty string command is required in YAML or via --entrypoint")
    if not args or not all(isinstance(item, str) and item for item in args):
        errors.append("non-empty string args are required in YAML or via --arg")

    node_selector = pod_spec.get("nodeSelector")
    if isinstance(node_selector, dict):
        existing = node_selector.get("kubernetes.io/hostname")
        if existing is not None and not isinstance(existing, str):
            errors.append("nodeSelector kubernetes.io/hostname must be a string")

    if errors:
        raise InputError("source Job violates the Phase 1 contract:\n- " + "\n- ".join(errors))

    return ValidatedJob(
        job=job,
        pod_spec=pod_spec,
        container=container,
        target_container=selected_name,
        command=list(command),
        args=list(args),
        gpu_resource=gpu_resource,
    )
