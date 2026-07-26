from __future__ import annotations

from pathlib import Path

import pytest

from profile_job_builder.errors import InputError
from profile_job_builder.yamlio import dump_yaml, load_yaml


def test_duplicate_keys_are_rejected(tmp_path: Path) -> None:
    source = tmp_path / "duplicate.yaml"
    source.write_text("kind: Job\nkind: Pod\n", encoding="utf-8")
    with pytest.raises(InputError, match="duplicate YAML mapping key"):
        load_yaml(str(source))


def test_multiple_documents_are_rejected(tmp_path: Path) -> None:
    source = tmp_path / "multiple.yaml"
    source.write_text("kind: Job\n---\nkind: Job\n", encoding="utf-8")
    with pytest.raises(InputError, match="exactly one YAML document"):
        load_yaml(str(source))


def test_multiline_strings_use_literal_style() -> None:
    rendered = dump_yaml({"script": "first\nsecond\n"})
    assert "script: |" in rendered
