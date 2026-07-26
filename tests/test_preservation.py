from __future__ import annotations

import copy

from profile_job_builder.builder import BuildConfig, build_profile_job
from profile_job_builder.preservation import compare_preservation


def test_external_fields_and_argv_are_preserved(source_job: dict) -> None:
    pod = source_job["spec"]["template"]["spec"]
    app = pod["containers"][0]
    app.update(
        {
            "imagePullPolicy": "IfNotPresent",
            "workingDir": "/workspace",
            "env": [{"name": "TRAIN_STEPS", "value": "10"}],
            "envFrom": [{"configMapRef": {"name": "training-env"}}],
            "securityContext": {"runAsNonRoot": True},
            "volumeMounts": [{"name": "dataset", "mountPath": "/data"}],
        }
    )
    pod.update(
        {
            "serviceAccountName": "trainer",
            "imagePullSecrets": [{"name": "registry"}],
            "tolerations": [{"key": "gpu", "operator": "Exists"}],
            "affinity": {"nodeAffinity": {}},
            "schedulerName": "default-scheduler",
            "priorityClassName": "training",
            "initContainers": [
                {
                    "name": "prepare",
                    "image": "busybox:1.36",
                    "command": ["sh"],
                    "args": ["-c", "true"],
                }
            ],
            "volumes": [{"name": "dataset", "emptyDir": {}}],
        }
    )
    result = build_profile_job(
        source_job,
        BuildConfig(target_container="app", name="external-profile"),
    )
    comparison = compare_preservation(source_job, result, "app")
    assert comparison["result"] == "pass"
    assert comparison["unexpected_changes"] == []


def test_unexpected_application_change_fails_comparison(source_job: dict) -> None:
    generated = build_profile_job(
        source_job,
        BuildConfig(target_container="app", name="external-profile"),
    )
    original = copy.deepcopy(source_job)
    generated["spec"]["template"]["spec"]["containers"][0]["image"] = "wrong:image"
    comparison = compare_preservation(original, generated, "app")
    assert comparison["result"] == "fail"
    assert any(
        item["path"] == "application.image"
        for item in comparison["unexpected_changes"]
    )
