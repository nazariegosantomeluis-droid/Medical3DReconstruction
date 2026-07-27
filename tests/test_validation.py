"""Dice/Jaccard/surface-distance and plausibility gating."""

from __future__ import annotations

import numpy as np

from medical3d.core.mesh_ops import MeshQualityReport
from medical3d.core.validation import (
    PLAUSIBLE_VOLUME_RANGES_ML,
    compute_overlap_metrics,
    dice_coefficient,
    jaccard_index,
    validate_segmentation,
)


def test_dice_identical_masks_is_one():
    mask = np.zeros((10, 10, 10), dtype=bool)
    mask[2:6, 2:6, 2:6] = True
    assert dice_coefficient(mask, mask) == 1.0
    assert jaccard_index(mask, mask) == 1.0


def test_dice_disjoint_masks_is_zero():
    a = np.zeros((10, 10, 10), dtype=bool)
    a[0:3, 0:3, 0:3] = True
    b = np.zeros((10, 10, 10), dtype=bool)
    b[7:10, 7:10, 7:10] = True
    assert dice_coefficient(a, b) == 0.0
    assert jaccard_index(a, b) == 0.0


def test_dice_partial_overlap_known_value():
    a = np.zeros((10, 10, 10), dtype=bool)
    a[0:4, 0:4, 0:4] = True  # 64 voxels
    b = np.zeros((10, 10, 10), dtype=bool)
    b[2:6, 2:6, 2:6] = True  # 64 voxels, overlap region [2:4]^3 = 8 voxels
    dice = dice_coefficient(a, b)
    expected = 2 * 8 / (64 + 64)
    assert dice == expected


def test_compute_overlap_metrics_zero_distance_for_identical_masks():
    mask = np.zeros((20, 20, 20), dtype=bool)
    mask[5:15, 5:15, 5:15] = True
    overlap = compute_overlap_metrics(mask, mask, spacing=(1.0, 1.0, 1.0))
    assert overlap.dice == 1.0
    assert overlap.mean_surface_distance_mm == 0.0
    assert overlap.hausdorff_distance_mm == 0.0


def test_validate_segmentation_flags_implausible_volume():
    quality = MeshQualityReport(is_watertight=True, is_winding_consistent=True, euler_number=2, num_bodies=1)
    report = validate_segmentation(organ="liver", volume_ml=5.0, mesh_quality=quality)
    assert not report.is_plausible_volume
    assert not report.passed
    assert any("outside the plausible" in w for w in report.warnings)


def test_validate_segmentation_passes_for_plausible_volume():
    low, high = PLAUSIBLE_VOLUME_RANGES_ML["liver"]
    mid = (low + high) / 2
    quality = MeshQualityReport(is_watertight=True, is_winding_consistent=True, euler_number=2, num_bodies=1)
    report = validate_segmentation(organ="liver", volume_ml=mid, mesh_quality=quality)
    assert report.is_plausible_volume
    assert report.passed


def test_validate_segmentation_fails_when_not_watertight():
    quality = MeshQualityReport(is_watertight=False, is_winding_consistent=True, euler_number=2, num_bodies=1)
    low, high = PLAUSIBLE_VOLUME_RANGES_ML["heart"]
    report = validate_segmentation(organ="heart", volume_ml=(low + high) / 2, mesh_quality=quality)
    assert not report.passed
