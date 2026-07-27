"""Liver pipeline (seeded region growing), run against a synthetic phantom.

See conftest.py / docs/VALIDATION.md for why this is a synthetic phantom
rather than real data: this repo does not ship an abdominal CT fixture.
The assertions check pipeline *mechanics* (converges, watertight, recovers
most of the known synthetic volume) rather than claiming clinical accuracy.
"""

from __future__ import annotations

import os

from medical3d.core.config import load_organ_config
from medical3d.organs.liver import LiverPipeline

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "liver.yaml")


def test_liver_pipeline_recovers_most_of_phantom_volume(liver_phantom_volume):
    volume, expected_volume_mm3 = liver_phantom_volume
    config = load_organ_config(CONFIG_PATH)
    pipeline = LiverPipeline(config)

    result = pipeline.run(volume)

    assert result.mesh.is_watertight
    assert result.mesh.is_winding_consistent
    assert result.mesh.body_count == 1

    recovered_fraction = result.metrics.volume_mm3 / expected_volume_mm3
    assert 0.5 <= recovered_fraction <= 1.1
