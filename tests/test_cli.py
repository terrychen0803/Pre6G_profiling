from __future__ import annotations

import json
import subprocess
import hashlib
from pathlib import Path

import profile_job_builder.cli as cli
from profile_job_builder.cli import _write_collected_metadata, build_parser, main
from profile_job_builder.yamlio import dump_yaml


def test_all_required_subcommands_are_exposed() -> None:
    output = build_parser().format_help()
    for command in ("inspect", "build", "diff", "validate", "run", "collect", "clean"):
        assert command in output


def test_build_and_validate_yolo_example(tmp_path: Path) -> None:
    source = Path("examples/yolo26/user-job.yaml")
    output = tmp_path / "profile.yaml"
    assert (
        main(
            [
                "validate",
                "--input",
                str(source),
                "--container",
                "trainer",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "build",
                "--input",
                str(source),
                "--container",
                "trainer",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    rendered = output.read_text(encoding="utf-8")
    assert "name: yolo26-train-profile" in rendered
    assert "profile-collector" in rendered
    assert "report=/profile-output/yolo26-train-profile/profile.nsys-rep" in rendered
    assert "nvidia.com/gpu.shared" in rendered


def test_invalid_input_returns_user_error(tmp_path: Path, capsys) -> None:
    source = tmp_path / "pod.yaml"
    source.write_text("apiVersion: v1\nkind: Pod\nmetadata:\n  name: no\n", encoding="utf-8")
    assert main(["validate", "--input", str(source)]) == 2
    assert "violates the Phase 1 contract" in capsys.readouterr().err


def test_collect_metadata_is_enriched(tmp_path: Path) -> None:
    report = tmp_path / "profile.nsys-rep"
    report.write_bytes(b"report")
    report_checksum = hashlib.sha256(b"report").hexdigest()
    (tmp_path / "profile-metadata.json").write_text(
        json.dumps(
            {
                "overall_status": "success",
                "failure_reason": "none",
                "expected_checksum": report_checksum,
                "actual_checksum": report_checksum,
                "report_exists": True,
                "report_valid": True,
                "stats_complete": True,
                "nsys_version": "NVIDIA Nsight Systems 2025.3.2",
                "finished_at": "done",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    job = {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": "train-profile",
            "annotations": {
                "profile-job-builder.local/source-job": "train",
                "profile-job-builder.local/original-command": '["python3","train.py"]',
            },
        },
        "status": {"completionTime": "2026-07-24T00:02:00Z"},
    }
    (tmp_path / "profile-job.yaml").write_text(dump_yaml(job), encoding="utf-8")
    pod = {
        "metadata": {"name": "train-profile-abc"},
        "spec": {
            "nodeName": "gx10-c206",
            "containers": [
                {
                    "name": "app",
                    "image": "example.invalid/train@sha256:abc",
                    "resources": {
                        "limits": {"nvidia.com/gpu.shared": "1"}
                    },
                },
                {"name": "profile-collector", "image": "ubuntu:24.04@sha256:arm64"},
            ],
        },
        "status": {
            "startTime": "2026-07-24T00:00:00Z",
            "containerStatuses": [
                {
                    "name": "app",
                    "state": {
                        "terminated": {"exitCode": 0, "reason": "Completed"}
                    },
                },
                {
                    "name": "profile-collector",
                    "state": {"terminated": {"exitCode": 0, "reason": "Completed"}},
                },
            ],
        },
    }
    (tmp_path / "pod.json").write_text(json.dumps(pod), encoding="utf-8")

    _write_collected_metadata(
        destination=tmp_path,
        job_name="train-profile",
        namespace="default",
        target_container="app",
    )

    metadata = json.loads(
        (tmp_path / "profile-metadata.json").read_text(encoding="utf-8")
    )
    assert metadata["sourceJob"] == "train"
    assert metadata["node"] == "gx10-c206"
    assert metadata["workloadCommand"] == ["python3", "train.py"]
    assert metadata["gpuResource"] == "nvidia.com/gpu.shared"
    assert metadata["gpuMode"] == "shared"
    assert metadata["applicationProfilerExitCode"] == 0
    assert metadata["collectorExitCode"] == 0
    assert metadata["overallStatus"] == "success"
    assert metadata["localChecksumMatch"] is True
    assert metadata["reportSize"] == 6
    assert len(metadata["reportSha256"]) == 64

    (tmp_path / "profile-metadata.json").write_text(
        json.dumps(
            {
                "overall_status": "success",
                "failure_reason": "none",
                "expected_checksum": "0" * 64,
                "actual_checksum": "0" * 64,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    mismatched = _write_collected_metadata(
        destination=tmp_path,
        job_name="train-profile",
        namespace="default",
        target_container="app",
    )
    assert mismatched["overallStatus"] == "failed"
    assert mismatched["failureReason"] == "local_checksum_mismatch"
    assert mismatched["localChecksumMatch"] is False


def test_collect_uses_existing_pod_without_creating_helper(
    tmp_path: Path, monkeypatch
) -> None:
    profile_yaml = tmp_path / "profile-job.yaml"
    profile_yaml.write_text(
        dump_yaml(
            {
                "apiVersion": "batch/v1",
                "kind": "Job",
                "metadata": {
                    "name": "train-profile",
                    "annotations": {
                        "profile-job-builder.local/source-job": "train",
                        "profile-job-builder.local/original-command": '["python3","train.py"]',
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    destination = tmp_path / "artifacts"
    commands: list[list[str]] = []
    acknowledged = False
    pod = {
        "metadata": {"name": "train-profile-abc"},
        "spec": {
            "nodeName": "gx10-c206",
            "containers": [
                {"name": "app", "image": "example.invalid/train:arm64"},
                {"name": "profile-collector", "image": "ubuntu:24.04"},
            ],
        },
        "status": {
            "containerStatuses": [
                {
                    "name": "profile-collector",
                    "state": {"running": {"startedAt": "2026-07-24T00:00:00Z"}},
                }
            ]
        },
    }

    def fake_run(command, **kwargs):
        nonlocal acknowledged
        command = list(command)
        commands.append(command)
        if "touch" in command:
            acknowledged = True
        if "cp" in command:
            destination.mkdir(parents=True, exist_ok=True)
            (destination / "profile.nsys-rep").write_bytes(b"report")
            checksum = hashlib.sha256(b"report").hexdigest()
            (destination / "profile-metadata.json").write_text(
                json.dumps(
                    {
                        "overall_status": "success",
                        "failure_reason": "none",
                        "expected_checksum": checksum,
                        "actual_checksum": checksum,
                        "report_exists": True,
                        "report_valid": True,
                        "stats_complete": True,
                        "nsys_version": "2025.3.2",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
        if "jsonpath={.items[0].metadata.name}" in command:
            stdout = "train-profile-abc"
        elif command[-2:] == ["-o", "json"]:
            if acknowledged:
                pod["status"]["containerStatuses"][0]["state"] = {
                    "terminated": {"exitCode": 0, "reason": "Completed"}
                }
            stdout = json.dumps(pod)
        else:
            stdout = ""
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    def fake_write(command, output: Path) -> None:
        commands.append(list(command))
        output.write_text("application log\n", encoding="utf-8")

    monkeypatch.setattr(cli, "run", fake_run)
    monkeypatch.setattr(cli, "write_command_output", fake_write)

    assert (
        main(
            [
                "collect",
                "--job",
                "train-profile",
                "--container",
                "app",
                "--profile-job-yaml",
                str(profile_yaml),
                "--destination",
                str(destination),
            ]
        )
        == 0
    )
    assert any("exec" in command for command in commands)
    assert any("cp" in command for command in commands)
    assert not any("create" in command for command in commands)
