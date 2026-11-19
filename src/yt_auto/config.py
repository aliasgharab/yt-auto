from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_config(path: Path | None = None) -> dict:
    path = path or ROOT / "config.yaml"
    with open(path) as f:
        cfg = yaml.safe_load(f)
    cfg["_root"] = ROOT
    return cfg
