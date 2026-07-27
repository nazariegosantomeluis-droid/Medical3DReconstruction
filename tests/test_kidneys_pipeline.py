"""Kidneys pipeline (bilateral boundary-aware level set), run against a synthetic phantom.

See conftest.py / docs/VALIDATION.md for why this is a synthetic phantom
rather than real data.
"""

from __future__ import annotations

import os

from medical3d.core.config import load_organ_config
from medical3d.organs.kidneys import KidneysPipeline

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "kidneys.yaml")


def test_kidneys_pipeline_finds_both_kidneys(kidneys_phantom_volume):
    volume, expected_total_volume_mm3 = kidneys_phantom_volume
    config = load_organ_config(CONFIG_PATH)
    pipeline = KidneysPipeline(config)

    result = pipeline.run(volume)

    assert result.mesh.is_watertight
    assert result.mesh.is_winding_consistent
    assert result.mesh.body_count == 2  # left + right kidney, found independently

    recovered_fraction = result.metrics.volume_mm3 / expected_total_volume_mm3
    assert 0.4 <= recovered_fraction <= 1.1
