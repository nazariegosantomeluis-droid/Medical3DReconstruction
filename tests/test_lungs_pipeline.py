"""Lungs pipeline, run end-to-end against the real chest CT fixture."""

from __future__ import annotations

import os

from medical3d.core.config import load_organ_config
from medical3d.organs.lungs import LungsPipeline

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "lungs.yaml")


def test_lungs_pipeline_end_to_end(real_ct_path):
    from medical3d.io import load_volume

    volume = load_volume(real_ct_path, modality="CT")
    config = load_organ_config(CONFIG_PATH)
    pipeline = LungsPipeline(config)

    result = pipeline.run(volume)

    assert result.mesh.is_watertight
    assert result.mesh.is_winding_consistent
    # Both lungs should be present and, after mesh cleanup, form a single
    # connected surface (they meet at the hilum/mediastinum in this scan).
    assert result.mesh.body_count <= 2

    assert 2000.0 <= result.metrics.volume_ml <= 7000.0
    assert result.validation.passed
    assert result.validation.is_plausible_volume
