"""Heart pipeline, run end-to-end against both supported modalities.

CT (boundary-aware level set) against the real chest CT fixture;
synchrotron (threshold + connected component) against a synthetic phantom
standing in for real ex-vivo tomography data (see
configs/heart_synchrotron.yaml and conftest.py for why).
"""

from __future__ import annotations

import os

from medical3d.core.config import load_organ_config
from medical3d.organs.heart import HeartPipeline

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(REPO_ROOT, "configs", "heart.yaml")
SYNCHROTRON_CONFIG_PATH = os.path.join(REPO_ROOT, "configs", "heart_synchrotron.yaml")


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


def test_heart_pipeline_synchrotron_end_to_end(synchrotron_heart_phantom_volume):
    volume, expected_tissue_volume_mm3 = synchrotron_heart_phantom_volume
    config = load_organ_config(SYNCHROTRON_CONFIG_PATH)
    pipeline = HeartPipeline(config)

    result = pipeline.run(volume)

    assert result.mesh.is_watertight
    assert result.mesh.body_count == 1

    recovered_fraction = result.metrics.volume_mm3 / expected_tissue_volume_mm3
    assert 0.5 <= recovered_fraction <= 1.1
