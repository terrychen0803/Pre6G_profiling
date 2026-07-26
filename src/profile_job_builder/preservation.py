from __future__ import annotations

import json
from typing import Any

from .builder import ORIGINAL_COMMAND_ANNOTATION


APP_FIELDS = (
    "name",
    "image",
    "imagePullPolicy",
    "workingDir",
    "resources",
    "securityContext",
    "envFrom",
)
POD_FIELDS = (
    "securityContext",
    "serviceAccountName",
    "imagePullSecrets",
    "tolerations",
    "affinity",
    "schedulerName",
    "priorityClassName",
)
RESERVED_ENV = {"TMPDIR", "PROFILE_OUTPUT_DIR"}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _container(document: dict[str, Any], name: str) -> dict[str, Any]:
    pod = _mapping(
        _mapping(_mapping(document.get("spec")).get("template")).get("spec")
    )
    matches = [
        item
        for item in _list(pod.get("containers"))
        if isinstance(item, dict) and item.get("name") == name
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one container named {name!r}; found {len(matches)}")
    return matches[0]


def _pod(document: dict[str, Any]) -> dict[str, Any]:
    return _mapping(
        _mapping(_mapping(document.get("spec")).get("template")).get("spec")
    )


def _env_without_reserved(container: dict[str, Any]) -> list[Any]:
    return [
        item
        for item in _list(container.get("env"))
        if not (
            isinstance(item, dict)
            and str(item.get("name", "")) in RESERVED_ENV
        )
    ]


def compare_preservation(
    source: dict[str, Any],
    generated: dict[str, Any],
    target_container: str,
) -> dict[str, Any]:
    preserved: list[str] = []
    controlled: list[str] = []
    unexpected: list[dict[str, Any]] = []

    source_app = _container(source, target_container)
    generated_app = _container(generated, target_container)
    source_pod = _pod(source)
    generated_pod = _pod(generated)

    def same(path: str, before: Any, after: Any) -> None:
        if before == after:
            preserved.append(path)
        else:
            unexpected.append({"path": path, "source": before, "generated": after})

    for field in APP_FIELDS:
        same(
            f"application.{field}",
            source_app.get(field),
            generated_app.get(field),
        )
    same(
        "application.env(non-reserved)",
        _env_without_reserved(source_app),
        _env_without_reserved(generated_app),
    )

    source_mounts = _list(source_app.get("volumeMounts"))
    generated_mounts = _list(generated_app.get("volumeMounts"))
    same(
        "application.volumeMounts(source-prefix)",
        source_mounts,
        generated_mounts[: len(source_mounts)],
    )

    source_volumes = _list(source_pod.get("volumes"))
    generated_volumes = _list(generated_pod.get("volumes"))
    same(
        "pod.volumes(source-prefix)",
        source_volumes,
        generated_volumes[: len(source_volumes)],
    )

    source_init = _list(source_pod.get("initContainers"))
    generated_init = _list(generated_pod.get("initContainers"))
    same(
        "pod.initContainers(source-prefix)",
        source_init,
        generated_init[: len(source_init)],
    )

    for field in POD_FIELDS:
        same(f"pod.{field}", source_pod.get(field), generated_pod.get(field))

    source_argv = [
        *_list(source_app.get("command")),
        *_list(source_app.get("args")),
    ]
    wrapper_args = _list(generated_app.get("args"))
    generated_argv = wrapper_args[2:] if len(wrapper_args) >= 2 else []
    same("application.argv", source_argv, generated_argv)

    annotations = _mapping(_mapping(generated.get("metadata")).get("annotations"))
    encoded = annotations.get(ORIGINAL_COMMAND_ANNOTATION)
    try:
        annotated_argv = json.loads(encoded) if isinstance(encoded, str) else None
    except json.JSONDecodeError:
        annotated_argv = None
    same("metadata.original-command-annotation", source_argv, annotated_argv)

    controlled.extend(
        [
            "metadata and Job execution fields",
            "application command/args profiler wrapper",
            "application reserved env",
            "profile-output and nsys-runtime mounts",
            "profile-output-init and profile-collector",
            "GX10 nodeSelector and RuntimeClass",
        ]
    )
    return {
        "result": "pass" if not unexpected else "fail",
        "targetContainer": target_container,
        "preserved": preserved,
        "controlled_changes": controlled,
        "unexpected_changes": unexpected,
    }
