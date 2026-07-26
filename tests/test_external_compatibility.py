from __future__ import annotations

import copy
from pathlib import Path

import pytest

from profile_job_builder.builder import BuildConfig, build_profile_job
from profile_job_builder.cli import main
from profile_job_builder.preservation import compare_preservation
from profile_job_builder.yamlio import load_yaml


EXTERNAL_CASES = (
    (
        Path("examples/external/gemma4-e2b/gx10-source-job.yaml"),
        "trainer",
    ),
)


@pytest.mark.parametrize(("source_path", "container"), EXTERNAL_CASES)
def test_external_cases_preserve_fields_and_source(
    source_path: Path, container: str
) -> None:
    source = load_yaml(str(source_path))
    original = copy.deepcopy(source)
    first = build_profile_job(
        source,
        BuildConfig(target_container=container, name=f"{source['metadata']['name']}-profile"),
    )
    second = build_profile_job(
        source,
        BuildConfig(target_container=container, name=f"{source['metadata']['name']}-profile"),
    )
    assert source == original
    assert first == second
    assert compare_preservation(source, first, container)["result"] == "pass"


def _remove_args(job: dict) -> None:
    job["spec"]["template"]["spec"]["containers"][0].pop("args")


def _enable_privileged(job: dict) -> None:
    job["spec"]["template"]["spec"]["containers"][0]["securityContext"] = {
        "privileged": True
    }


def _add_second_container(job: dict) -> None:
    job["spec"]["template"]["spec"]["containers"].append(
        {
            "name": "sidecar",
            "image": "busybox:1.36",
            "command": ["sh"],
            "args": ["-c", "true"],
        }
    )


def _request_two_gpus(job: dict) -> None:
    app = job["spec"]["template"]["spec"]["containers"][0]
    app["resources"]["limits"]["nvidia.com/gpu.shared"] = "2"


def _reserve_output_mount(job: dict) -> None:
    pod = job["spec"]["template"]["spec"]
    pod.setdefault("volumes", []).append({"name": "user-output", "emptyDir": {}})
    pod["containers"][0].setdefault("volumeMounts", []).append(
        {"name": "user-output", "mountPath": "/profile-output"}
    )


@pytest.mark.parametrize(
    ("case_id", "mutation"),
    [
        ("n1-missing-args", _remove_args),
        ("n2-privileged", _enable_privileged),
        ("n3-multiple-containers", _add_second_container),
        ("n4-two-gpus", _request_two_gpus),
        ("n5-reserved-mount", _reserve_output_mount),
    ],
)
def test_external_rejections_leave_no_partial_output(
    tmp_path: Path, case_id: str, mutation
) -> None:
    source = load_yaml(
        "examples/external/gemma4-e2b/gx10-source-job.yaml"
    )
    mutation(source)
    source_path = tmp_path / f"{case_id}.yaml"
    output_path = tmp_path / f"{case_id}-profile.yaml"

    import yaml

    source_path.write_text(
        yaml.safe_dump(source, sort_keys=False),
        encoding="utf-8",
    )
    result = main(
        [
            "build",
            "--input",
            str(source_path),
            "--container",
            "trainer",
            "--name",
            f"{case_id}-profile",
            "--output",
            str(output_path),
        ]
    )
    assert result == 2
    assert not output_path.exists()
