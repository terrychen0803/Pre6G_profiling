from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

import pytest

from profile_job_builder.builder import _collector_script


VALID_REPORT = b"NVIDIA Tegra Profiler Report 2025\nVALID\n"
CORRUPTED_REPORT = b"NVIDIA Tegra Profiler Report 2025\nCORRUPTED\n"


def _fake_nsys(path: Path) -> None:
    path.write_text(
        """#!/bin/sh
set -eu
if [ "${1:-}" = "--version" ]; then
  echo "NVIDIA Nsight Systems version test"
  exit 0
fi
if [ "${1:-}" != "stats" ]; then
  exit 90
fi
all_args="$*"
for argument in "$@"; do
  report="$argument"
done
if grep -q '^not-a-valid' "$report"; then
  if [ "${SOFT_PARSE_ERROR:-0}" = 1 ]; then
    echo "Exportation error: Version tag is not found in the stream."
    echo "ERROR: Database file does not exist."
    exit 0
  fi
  echo "invalid report" >&2
  exit 91
fi
if grep -q 'CORRUPTED' "$report"; then
  if [ "${SOFT_PARSE_ERROR:-0}" = 1 ]; then
    echo "Exportation error: Section Table Reference magic number mismatch."
    echo "ERROR: Database file does not exist."
    exit 0
  fi
  echo "truncated report" >&2
  exit 92
fi
if [ "${FAIL_REPORT:-}" != "" ] && echo "$all_args" | grep -q "$FAIL_REPORT"; then
  echo "required report failed" >&2
  exit 93
fi
if [ "${SOFT_FAIL_REPORT:-}" != "" ] && echo "$all_args" | grep -q "$SOFT_FAIL_REPORT"; then
  echo "Exportation error: simulated zero-exit failure"
  exit 0
fi
if [ "${FAIL_CSV:-0}" = 1 ] && echo "$all_args" | grep -q -- '--format=csv'; then
  echo "csv export failed" >&2
  exit 94
fi
printf 'summary for %s\\n' "$all_args"
printf '%s\\n' \
  'OS Runtime Summary' \
  'CUDA API Summary'
if [ "${OMIT_KERNEL_SUMMARY:-0}" != 1 ]; then
  printf '%s\\n' 'CUDA GPU Kernel Summary'
fi
printf '%s\\n' \
  'CUDA GPU MemOps Summary (by Time)' \
  'CUDA GPU MemOps Summary (by Size)'
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _run_collector(
    tmp_path: Path,
    *,
    report: bytes | None,
    application_exit: int = 0,
    expected_checksum: str | None = None,
    extra_env: dict[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], dict, Path]:
    output = tmp_path / "output"
    output.mkdir()
    (output / ".application-finished").write_text(
        f"{application_exit}\n", encoding="utf-8"
    )
    if report is not None:
        (output / "profile.nsys-rep").write_bytes(report)
        checksum = expected_checksum or hashlib.sha256(report).hexdigest()
        (output / ".expected-sha256").write_text(
            checksum + "\n", encoding="utf-8"
        )

    fake_nsys = tmp_path / "fake-nsys"
    _fake_nsys(fake_nsys)
    script = tmp_path / "collector.sh"
    script.write_text(_collector_script(str(output), 30), encoding="utf-8")

    environment = os.environ.copy()
    environment["NSYS_BINARY_OVERRIDE"] = str(fake_nsys)
    environment.update(extra_env or {})
    process = subprocess.Popen(
        ["/bin/sh", "-eu", str(script)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
    )
    deadline = time.monotonic() + 5
    while not (output / ".collector-ready").exists():
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            pytest.fail(
                f"collector exited before readiness: {process.returncode}\n"
                f"stdout={stdout}\nstderr={stderr}"
            )
        if time.monotonic() >= deadline:
            process.kill()
            pytest.fail("collector did not publish readiness within 5 seconds")
        time.sleep(0.02)
    (output / ".collected").touch()
    stdout, stderr = process.communicate(timeout=5)
    completed = subprocess.CompletedProcess(
        process.args, process.returncode, stdout, stderr
    )
    metadata = json.loads(
        (output / "profile-metadata.json").read_text(encoding="utf-8")
    )
    return completed, metadata, output


@pytest.mark.parametrize(
    ("report", "reason", "exit_code"),
    [
        (None, "missing_report", 20),
        (b"", "empty_report", 21),
        (b"not-a-valid-nsys-report\n", "parse_failure", 25),
        (CORRUPTED_REPORT, "corrupted_report", 24),
    ],
)
def test_collector_rejects_missing_empty_invalid_and_corrupted_reports(
    tmp_path: Path,
    report: bytes | None,
    reason: str,
    exit_code: int,
) -> None:
    completed, metadata, output = _run_collector(tmp_path, report=report)

    assert completed.returncode == exit_code
    assert metadata["overall_status"] == "failed"
    assert metadata["failure_reason"] == reason
    assert metadata["collector_exit_code"] == exit_code
    assert not (output / "nsys-stats.txt").exists()
    assert not (output / "nsys-stats.csv").exists()


def test_collector_rejects_checksum_mismatch(tmp_path: Path) -> None:
    completed, metadata, output = _run_collector(
        tmp_path,
        report=VALID_REPORT,
        expected_checksum="0" * 64,
    )

    assert completed.returncode == 23
    assert metadata["failure_reason"] == "integrity_failure"
    assert metadata["checksum_match"] is False
    assert not (output / "nsys-stats.txt").exists()


@pytest.mark.parametrize(
    ("report", "reason", "exit_code"),
    [
        (b"not-a-valid-nsys-report\n", "parse_failure", 25),
        (CORRUPTED_REPORT, "corrupted_report", 24),
    ],
)
def test_collector_rejects_parser_errors_even_when_nsys_exits_zero(
    tmp_path: Path,
    report: bytes,
    reason: str,
    exit_code: int,
) -> None:
    completed, metadata, output = _run_collector(
        tmp_path,
        report=report,
        extra_env={"SOFT_PARSE_ERROR": "1"},
    )

    assert completed.returncode == exit_code
    assert metadata["failure_reason"] == reason
    assert (output / "nsys-stats.stderr.txt").stat().st_size > 0
    assert not (output / "nsys-stats.txt").exists()


@pytest.mark.parametrize(
    "extra_env",
    [
        {"FAIL_REPORT": "cuda_gpu_kern_sum"},
        {"FAIL_CSV": "1"},
        {"SOFT_FAIL_REPORT": "cuda_gpu_kern_sum"},
        {"OMIT_KERNEL_SUMMARY": "1"},
    ],
)
def test_collector_fails_when_any_required_stats_export_fails(
    tmp_path: Path, extra_env: dict[str, str]
) -> None:
    completed, metadata, output = _run_collector(
        tmp_path,
        report=VALID_REPORT,
        extra_env=extra_env,
    )

    assert completed.returncode == 26
    assert metadata["failure_reason"] == "stats_failure"
    assert metadata["report_valid"] is True
    assert metadata["stats_complete"] is False
    assert (output / "nsys-stats.stderr.txt").stat().st_size > 0
    assert not (output / "nsys-stats.txt").exists()


def test_application_failure_preserves_valid_stats_but_fails_run(
    tmp_path: Path,
) -> None:
    completed, metadata, output = _run_collector(
        tmp_path,
        report=VALID_REPORT,
        application_exit=7,
    )

    assert completed.returncode == 27
    assert metadata["failure_reason"] == "application_exit_nonzero"
    assert metadata["application_exit_code"] == 7
    assert metadata["report_valid"] is True
    assert metadata["stats_complete"] is True
    assert (output / "nsys-stats.txt").stat().st_size > 0
    assert (output / "nsys-stats.csv").stat().st_size > 0


def test_valid_report_requires_all_stats_and_succeeds(tmp_path: Path) -> None:
    completed, metadata, output = _run_collector(
        tmp_path,
        report=VALID_REPORT,
    )

    assert completed.returncode == 0
    assert metadata["overall_status"] == "success"
    assert metadata["failure_reason"] == "none"
    assert metadata["report_exists"] is True
    assert metadata["report_size_bytes"] == len(VALID_REPORT)
    assert metadata["report_valid"] is True
    assert metadata["checksum_match"] is True
    assert metadata["stats_complete"] is True
    assert (output / "nsys-stats.txt").stat().st_size > 0
    assert (output / "nsys-stats.csv").stat().st_size > 0
