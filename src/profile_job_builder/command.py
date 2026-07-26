from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Sequence

from .errors import CommandError


def run(
    command: Sequence[str],
    *,
    input_text: str | None = None,
    capture: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(command),
            input=input_text,
            text=True,
            check=check,
            capture_output=capture,
        )
    except FileNotFoundError as exc:
        raise CommandError(f"required command is not installed: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        suffix = f": {detail}" if detail else ""
        raise CommandError(f"command failed ({exc.returncode}): {' '.join(command)}{suffix}") from exc


def write_command_output(command: Sequence[str], destination: Path) -> None:
    completed = run(command, capture=True)
    destination.write_text(completed.stdout, encoding="utf-8")
