"""Heart pipeline (boundary-aware level set), run end-to-end against the real chest CT fixture."""

from __future__ import annotations

import os

from medical3d.core.config import load_organ_config
from medical3d.organs.heart import HeartPipeline

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "heart.yaml")


def test_heart_pipeline_end_to_end(real_ct_path):
    from medical3d.io import load_volume

    volume = load_volume(real_ct_path, modality="CT")
    config = load_organ_config(CONFIG_PATH)
    pipeline = HeartPipeline(config)

    result = pipeline.run(volume)

    assert result.mesh.is_watertight
    assert result.mesh.is_winding_consistent
    assert result.mesh.body_count == 1

    assert 300.0 <= result.metrics.volume_ml <= 900.0
    assert result.validation.passed
