"""Read KEY=value lines from a local .env file without adding a dependency."""

import os
from pathlib import Path

from procurement.shared.references import PROJECT_ROOT


def load_env(path: Path | None = None) -> None:
    """Fill os.environ from .env. Variables already set in the shell win."""
    path = path or PROJECT_ROOT / '.env'
    try:
        lines = path.read_text(encoding='utf-8').splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        name, value = line.split('=', 1)
        name, value = name.strip(), value.strip().strip('"').strip("'")
        if name and value and name not in os.environ:
            os.environ[name] = value
