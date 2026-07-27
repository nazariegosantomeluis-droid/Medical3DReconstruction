"""YAML-driven configuration for organ pipelines.

Keeping thresholds, seed heuristics, and mesh post-processing parameters in
config files (instead of hard-coded in pipeline code) is what makes a run
reproducible and auditable: the exact parameters used to produce a given
mesh are recorded alongside the pipeline, not buried in source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import yaml


@dataclass(frozen=True)
class OrganConfig:
    organ: str
    modality: str
    mesh_smoothing_sigma: float = 1.0
    mesh_taubin_iterations: int = 10
    mesh_decimate_target_fraction: float = 0.5
    params: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.params.get(key, default)


def load_organ_config(path: str) -> OrganConfig:
    with open(path, "r") as f:
        raw = yaml.safe_load(f)

    if raw is None or "organ" not in raw:
        raise ValueError(f"Invalid organ config '{path}': missing required 'organ' key")

    known_fields = {"organ", "modality", "mesh_smoothing_sigma", "mesh_taubin_iterations", "mesh_decimate_target_fraction"}
    params = {k: v for k, v in raw.items() if k not in known_fields}

    return OrganConfig(
        organ=raw["organ"],
        modality=raw.get("modality", "CT"),
        mesh_smoothing_sigma=float(raw.get("mesh_smoothing_sigma", 1.0)),
        mesh_taubin_iterations=int(raw.get("mesh_taubin_iterations", 10)),
        mesh_decimate_target_fraction=float(raw.get("mesh_decimate_target_fraction", 0.5)),
        params=params,
    )
