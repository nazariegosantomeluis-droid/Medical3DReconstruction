"""Brain pipeline (synchrotron-only), run end-to-end against a synthetic phantom.

See conftest.py / docs/ORGAN_PIPELINES.md for why this is a synthetic
phantom rather than real data in the automated test suite: the real
LADAF-2021-17 archive is >100MB and not committed to the repository.
"""

from __future__ import annotations

import os

import pytest

from medical3d.core.config import load_organ_config
from medical3d.organs.brain import BrainPipeline

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNCHROTRON_CONFIG_PATH = os.path.join(REPO_ROOT, "configs", "brain_synchrotron.yaml")


def test_brain_pipeline_synchrotron_end_to_end(synchrotron_brain_phantom_volume):
    volume, expected_tissue_volume_mm3 = synchrotron_brain_phantom_volume
    config = load_organ_config(SYNCHROTRON_CONFIG_PATH)
    pipeline = BrainPipeline(config)

    result = pipeline.run(volume)

    assert result.mesh.is_watertight
    assert result.mesh.body_count == 1

    recovered_fraction = result.metrics.volume_mm3 / expected_tissue_volume_mm3
    assert 0.5 <= recovered_fraction <= 1.1


def test_brain_pipeline_rejects_non_synchrotron_modality(synchrotron_brain_phantom_volume):
    volume, _ = synchrotron_brain_phantom_volume
    ct_volume = volume.__class__(
        array=volume.array, spacing=volume.spacing, origin=volume.origin,
        direction=volume.direction, modality="CT", source_path=volume.source_path,
    )
    config = load_organ_config(SYNCHROTRON_CONFIG_PATH)
    pipeline = BrainPipeline(config)

    with pytest.raises(ValueError, match="synchrotron"):
        pipeline.run(ct_volume)
