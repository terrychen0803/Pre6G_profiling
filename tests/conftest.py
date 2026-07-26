from __future__ import annotations

import copy

import pytest


@pytest.fixture
def source_job() -> dict:
    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": "train",
            "namespace": "ml",
            "uid": "server-value",
            "resourceVersion": "42",
            "labels": {"team": "perf"},
        },
        "spec": {
            "selector": {"matchLabels": {"controller-uid": "server-value"}},
            "template": {
                "metadata": {"labels": {"team": "perf"}},
                "spec": {
                    "restartPolicy": "OnFailure",
                    "containers": [
                        {
                            "name": "app",
                            "image": "example.invalid/train:arm64",
                            "command": ["python3"],
                            "args": ["train.py", "--epochs", "2"],
                            "env": [{"name": "KEEP", "value": "yes"}],
                            "resources": {
                                "requests": {"nvidia.com/gpu.shared": "1"},
                                "limits": {"nvidia.com/gpu.shared": "1"},
                            },
                            "volumeMounts": [
                                {"name": "data", "mountPath": "/data"}
                            ],
                        }
                    ],
                    "volumes": [{"name": "data", "emptyDir": {}}],
                },
            },
        },
    }


@pytest.fixture
def clone():
    return copy.deepcopy
