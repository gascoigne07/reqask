"""Версия агента для паспорта прогона: версия пакета и коммит Git."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from . import __version__


def _git(*args: str) -> str | None:
    repo = Path(__file__).resolve().parents[2]
    try:
        done = subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=5, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def agent_version() -> str:
    commit = os.getenv("REQASK_COMMIT") or _git("rev-parse", "--short", "HEAD")
    if not commit:
        return f"{__version__} (без коммита)"
    dirty = _git("status", "--porcelain", "--untracked-files=no")
    suffix = ", есть незакоммиченные правки" if dirty else ""
    return f"{__version__}, коммит {commit}{suffix}"
