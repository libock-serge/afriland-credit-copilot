"""
Tools available to agents. In this offline build they are local/simulated, but each is
written as a clean function an agent 'calls' so swapping in a real implementation
(a real sanctions API, a real OCR service) is a one-function change.
"""
from __future__ import annotations
import json
import os


def read_memory(case_dir: str, name: str):
    """Read a JSON artifact a previous agent wrote into the case's memory folder."""
    path = os.path.join(case_dir, name)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_memory(case_dir: str, name: str, obj) -> str:
    """Persist a structured artifact to the case's memory folder (long-term memory)."""
    os.makedirs(case_dir, exist_ok=True)
    path = os.path.join(case_dir, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    return path


# --- simulated external tools ---

_SANCTIONS_LIST = {"redline trading sarl", "global X holdings"}  # tiny demo list


def screen_sanctions(name: str) -> bool:
    """Stand-in for a sanctions/PEP screening API."""
    return name.strip().lower() in _SANCTIONS_LIST


def fetch_sector_benchmark(sector: str) -> dict:
    """Stand-in for an internal benchmark service."""
    table = {
        "retail": {"typical_margin_pct": 12, "typical_dscr": 1.4},
        "agriculture": {"typical_margin_pct": 18, "typical_dscr": 1.3},
        "manufacturing": {"typical_margin_pct": 15, "typical_dscr": 1.5},
        "services": {"typical_margin_pct": 22, "typical_dscr": 1.6},
        "transport": {"typical_margin_pct": 14, "typical_dscr": 1.35},
    }
    return table.get(sector.lower(), {"typical_margin_pct": 15, "typical_dscr": 1.4})
