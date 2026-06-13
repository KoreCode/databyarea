"""Small local environment loader for DataByArea scripts.

Loads optional `.env.local` / `.env` files without adding a runtime dependency.
Existing process environment values win over file values.
"""

from __future__ import annotations

import os
from pathlib import Path


def load_local_env(root: Path) -> None:
    for name in (".env.local", ".env"):
        path = root / name
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
