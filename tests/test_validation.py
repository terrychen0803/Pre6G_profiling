from __future__ import annotations

import pytest

from profile_job_builder.errors import InputError
from profile_job_builder.validation import validate_source_job


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda job: job["spec"]["template"]["spec"].update({"hostPID": True}),
            "hostPID is forbidden",
        ),
        (
            lambda job: job["spec"]["template"]["spec"].update(
                {"shareProcessNamespace": True}
            ),
            "shareProcessNamespace is forbidden",
        ),
        (
            lambda job: job["spec"]["template"]["spec"]["containers"][0].update(
                {"securityContext": {"privileged": True}}
            ),
            "privileged securityContext is forbidden",
        ),
        (
            lambda job: job["spec"]["template"]["spec"]["containers"][0].update(
                {"securityContext": {"capabilities": {"add": ["SYS_PTRACE"]}}}
            ),
            "SYS_PTRACE capability is forbidden",
        ),
    ],
)
def test_forbidden_permissions_are_rejected(
    source_job: dict, mutation, message: str
) -> None:
    mutation(source_job)
    with pytest.raises(InputError, match=message):
        validate_source_job(source_job, "app")


def test_multiple_containers_are_rejected(source_job: dict, clone) -> None:
    app = source_job["spec"]["template"]["spec"]["containers"][0]
    sidecar = clone(app)
    sidecar["name"] = "sidecar"
    source_job["spec"]["template"]["spec"]["containers"].append(sidecar)
    with pytest.raises(InputError, match="exactly one application container"):
        validate_source_job(source_job, "app")


@pytest.mark.parametrize("gpu", ["0", "2", "not-a-number"])
def test_exactly_one_gpu_is_required(source_job: dict, gpu) -> None:
    limits = source_job["spec"]["template"]["spec"]["containers"][0]["resources"][
        "limits"
    ]
    limits["nvidia.com/gpu.shared"] = gpu
    with pytest.raises(InputError, match="exactly 1"):
        validate_source_job(source_job, "app")


def test_gpu_resource_is_required(source_job: dict) -> None:
    container = source_job["spec"]["template"]["spec"]["containers"][0]
    container["resources"]["limits"].clear()
    with pytest.raises(InputError, match="exactly one supported GPU limit"):
        validate_source_job(source_job, "app")


def test_dedicated_gpu_resource_remains_supported(source_job: dict) -> None:
    container = source_job["spec"]["template"]["spec"]["containers"][0]
    container["resources"]["limits"] = {"nvidia.com/gpu": "1"}
    container["resources"]["requests"] = {"nvidia.com/gpu": "1"}
    validated = validate_source_job(source_job, "app")
    assert validated.gpu_resource == "nvidia.com/gpu"


def test_shared_and_dedicated_gpu_cannot_be_combined(source_job: dict) -> None:
    container = source_job["spec"]["template"]["spec"]["containers"][0]
    container["resources"]["limits"]["nvidia.com/gpu"] = "1"
    with pytest.raises(InputError, match="exactly one supported GPU limit"):
        validate_source_job(source_job, "app")


def test_reserved_volume_and_mount_are_rejected(source_job: dict) -> None:
    pod = source_job["spec"]["template"]["spec"]
    pod["volumes"].append({"name": "profile-output", "emptyDir": {}})
    pod["containers"][0]["volumeMounts"].append(
        {"name": "other", "mountPath": "/opt/profiler/nsys"}
    )
    with pytest.raises(InputError) as raised:
        validate_source_job(source_job, "app")
    assert "reserved volume name conflict" in str(raised.value)
    assert "reserved mount path conflict" in str(raised.value)


def test_missing_command_is_rejected_without_override(source_job: dict) -> None:
    source_job["spec"]["template"]["spec"]["containers"][0].pop("command")
    with pytest.raises(InputError, match="command is required"):
        validate_source_job(source_job, "app")


def test_reserved_init_container_is_rejected(source_job: dict) -> None:
    source_job["spec"]["template"]["spec"]["initContainers"] = [
        {"name": "profile-output-init", "image": "example.invalid/init"}
    ]
    with pytest.raises(InputError, match="reserved init container name conflict"):
        validate_source_job(source_job, "app")


def test_ephemeral_containers_are_rejected(source_job: dict) -> None:
    source_job["spec"]["template"]["spec"]["ephemeralContainers"] = [
        {"name": "debugger", "image": "example.invalid/debug"}
    ]
    with pytest.raises(InputError, match="ephemeralContainers"):
        validate_source_job(source_job, "app")


def test_privileged_init_container_is_rejected(source_job: dict) -> None:
    source_job["spec"]["template"]["spec"]["initContainers"] = [
        {
            "name": "setup",
            "image": "example.invalid/init",
            "securityContext": {"privileged": True},
        }
    ]
    with pytest.raises(InputError, match="privileged securityContext"):
        validate_source_job(source_job, "app")
