from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import Any, TextIO

import yaml

from .errors import InputError


class UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


class ReadableDumper(yaml.SafeDumper):
    """Safe dumper that renders scripts as literal blocks."""


def _represent_string(dumper: ReadableDumper, value: str) -> yaml.ScalarNode:
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


ReadableDumper.add_representer(str, _represent_string)


def _construct_mapping(
    loader: UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise InputError(f"YAML mapping key is not hashable: {key!r}") from exc
        if duplicate:
            raise InputError(f"duplicate YAML mapping key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def _read_stream(path: str) -> tuple[str, str]:
    if path == "-":
        return sys.stdin.read(), "stdin"
    source = Path(path)
    try:
        return source.read_text(encoding="utf-8"), str(source)
    except OSError as exc:
        raise InputError(f"cannot read {source}: {exc}") from exc


def load_yaml(path: str) -> dict[str, Any]:
    text, source = _read_stream(path)
    try:
        documents = list(yaml.load_all(text, Loader=UniqueKeyLoader))
    except (yaml.YAMLError, InputError) as exc:
        raise InputError(f"invalid YAML in {source}: {exc}") from exc
    if len(documents) != 1:
        raise InputError(
            f"{source} must contain exactly one YAML document; found {len(documents)}"
        )
    document = documents[0]
    if not isinstance(document, dict):
        raise InputError(f"{source} must contain a YAML mapping at the document root")
    return document


def dump_yaml(document: dict[str, Any], stream: TextIO | None = None) -> str:
    rendered = yaml.dump(
        document,
        Dumper=ReadableDumper,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=100,
    )
    if stream is not None:
        stream.write(rendered)
    return rendered


def yaml_bytes(document: dict[str, Any]) -> io.BytesIO:
    return io.BytesIO(dump_yaml(document).encode("utf-8"))
