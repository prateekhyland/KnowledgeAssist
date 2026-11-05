"""Load the sources.yaml ingestion configuration."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCES = ROOT / "sources.yaml"


def load_sources(path: str | Path | None = None) -> list[dict[str, Any]]:
    """Return the list of knowledge_bases from sources.yaml."""
    p = Path(path) if path else DEFAULT_SOURCES
    if not p.exists():
        raise FileNotFoundError(
            f"Sources file not found: {p}. Copy sources.example.yaml to sources.yaml "
            "and edit it."
        )
    with open(p, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    kbs = data.get("knowledge_bases", [])
    if not kbs:
        raise ValueError(f"No knowledge_bases defined in {p}")
    return kbs
