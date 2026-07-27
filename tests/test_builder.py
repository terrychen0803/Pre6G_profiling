from __future__ import annotations

import copy

import pytest

from profile_job_builder.builder import (
    NSYS_BINARY,
    ORIGINAL_COMMAND_ANNOTATION,
    PROFILE_LABEL,
    BuildConfig,
    build_profile_job,
)
from profile_job_builder.errors import InputError


def test_build_preserves_source_and_wraps_command(source_job: dict) -> None:
    original = copy.deepcopy(source_job)

    result = build_profile_job(source_job, BuildConfig(target_container="app"))

    assert source_job == original
    assert result["metadata"]["name"] == "train-profile"
    assert result["metadata"]["labels"][PROFILE_LABEL] == "true"
    assert (
        result["metadata"]["annotations"][ORIGINAL_COMMAND_ANNOTATION]
        == '["python3","train.py","--epochs","2"]'
    )
    assert "uid" not in result["metadata"]
    assert "resourceVersion" not in result["metadata"]
    assert "selector" not in result["spec"]
    assert result["spec"]["parallelism"] == 1
    assert result["spec"]["completions"] == 1
    assert result["spec"]["backoffLimit"] == 0

    pod_spec = result["spec"]["template"]["spec"]
    assert pod_spec["restartPolicy"] == "Never"
    assert pod_spec["runtimeClassName"] == "nvidia"
    assert pod_spec["nodeSelector"]["kubernetes.io/hostname"] == "gx10-c206"
    assert len(pod_spec["containers"]) == 2

    app = pod_spec["containers"][0]
    assert app["command"] == ["/bin/sh", "-ceu"]
    assert app["args"][-4:] == ["python3", "train.py", "--epochs", "2"]
    assert NSYS_BINARY in app["args"][0]
    assert "--sample=none" in app["args"][0]
    assert "--cpuctxsw=none" in app["args"][0]
    assert ".application-finished" in app["args"][0]
    assert ".expected-sha256" in app["args"][0]
    assert app["image"] == original["spec"]["template"]["spec"]["containers"][0]["image"]
    assert app["resources"] == original["spec"]["template"]["spec"]["containers"][0]["resources"]
    assert {"name": "KEEP", "value": "yes"} in app["env"]

    collector = pod_spec["containers"][1]
    assert collector["name"] == "profile-collector"
    assert "nvidia.com/gpu" not in collector["resources"].get("limits", {})
    assert "nvidia.com/gpu" not in collector["resources"].get("requests", {})
    assert "nvidia.com/gpu.shared" not in collector["resources"].get("limits", {})
    assert "nvidia.com/gpu.shared" not in collector["resources"].get("requests", {})
    assert ".collector-ready" in collector["args"][0]
    assert ".collected" in collector["args"][0]
    init_script = pod_spec["initContainers"][-1]["args"][0]
    assert "refusing to reuse non-empty artifact directory" in init_script
    assert collector["securityContext"]["allowPrivilegeEscalation"] is False
    assert "SYS_PTRACE" not in collector["securityContext"]["capabilities"]["drop"]

    volumes = {item["name"]: item for item in pod_spec["volumes"]}
    assert volumes["nsys-runtime"]["hostPath"]["type"] == "Directory"
    assert (
        volumes["profile-output"]["persistentVolumeClaim"]["claimName"]
        == "profile-artifacts"
    )


def test_build_without_collector_uses_empty_dir(source_job: dict) -> None:
    result = build_profile_job(
        source_job,
        BuildConfig(
            target_container="app",
            include_collector=False,
            artifact_pvc=None,
        ),
    )
    pod_spec = result["spec"]["template"]["spec"]
    assert len(pod_spec["containers"]) == 1
    output = next(item for item in pod_spec["volumes"] if item["name"] == "profile-output")
    assert output["emptyDir"] == {}


def test_build_accepts_explicit_nsys_profile_arguments(source_job: dict) -> None:
    profile_args = (
        "--trace=cuda,nvtx,cudnn,cublas,osrt",
        "--gpu-metrics-devices=all",
        "--sample=process-tree",
        "--cpuctxsw=process-tree",
        "--pytorch=autograd-shapes-nvtx,functions-trace",
        "--cuda-memory-usage=true",
        "--osrt-file-access=true",
    )
    result = build_profile_job(
        source_job,
        BuildConfig(target_container="app", nsys_profile_args=profile_args),
    )
    script = result["spec"]["template"]["spec"]["containers"][0]["args"][0]
    for argument in profile_args:
        assert argument in script
    assert "--sample=none" not in script


def test_build_adds_capability_only_to_application_container(source_job: dict) -> None:
    result = build_profile_job(
        source_job,
        BuildConfig(
            target_container="app",
            application_capabilities=("SYS_ADMIN",),
        ),
    )
    containers = result["spec"]["template"]["spec"]["containers"]
    app = containers[0]
    collector = containers[1]
    assert app["securityContext"] == {
        "allowPrivilegeEscalation": False,
        "capabilities": {"add": ["SYS_ADMIN"]},
    }
    assert collector["securityContext"]["capabilities"] == {"drop": ["ALL"]}


def test_build_is_deterministic(source_job: dict) -> None:
    config = BuildConfig(target_container="app")
    assert build_profile_job(source_job, config) == build_profile_job(source_job, config)


def test_existing_different_node_is_rejected(source_job: dict) -> None:
    source_job["spec"]["template"]["spec"]["nodeSelector"] = {
        "kubernetes.io/hostname": "another-node"
    }
    with pytest.raises(InputError, match="refusing to replace"):
        build_profile_job(source_job, BuildConfig(target_container="app"))


def test_existing_different_runtime_class_is_rejected(source_job: dict) -> None:
    source_job["spec"]["template"]["spec"]["runtimeClassName"] = "runc"
    with pytest.raises(InputError, match="GX10 profiling requires"):
        build_profile_job(source_job, BuildConfig(target_container="app"))


def test_long_name_is_dns_bounded_and_stable(source_job: dict) -> None:
    source_job["metadata"]["name"] = "a" * 63
    first = build_profile_job(source_job, BuildConfig(target_container="app"))
    second = build_profile_job(source_job, BuildConfig(target_container="app"))
    assert first["metadata"]["name"] == second["metadata"]["name"]
    assert len(first["metadata"]["name"]) <= 63


def test_entrypoint_override_replaces_missing_command(source_job: dict) -> None:
    app = source_job["spec"]["template"]["spec"]["containers"][0]
    app.pop("command")
    app.pop("args")
    result = build_profile_job(
        source_job,
        BuildConfig(
            target_container="app",
            entrypoint="python3",
            args=("train.py",),
        ),
    )
    assert result["spec"]["template"]["spec"]["containers"][0]["args"][-2:] == [
        "python3",
        "train.py",
    ]


def test_collector_requires_persistent_volume(source_job: dict) -> None:
    with pytest.raises(InputError, match="artifact-pvc"):
        build_profile_job(
            source_job,
            BuildConfig(
                target_container="app",
                include_collector=True,
                artifact_pvc=None,
            ),
        )
