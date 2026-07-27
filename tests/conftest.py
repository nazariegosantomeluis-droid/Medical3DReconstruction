"""Shared test fixtures: synthetic phantoms and the real CT fixture.

Liver and kidney pipelines are validated here against synthetic phantoms
rather than real abdominal CT, because the only real scan committed to
this repository (``data/volumes/CTChest.nrrd``) is a chest CT and does not
include the abdomen. The phantoms are not a substitute for validation
against expert-labeled clinical data (see docs/VALIDATION.md) — they exist
to prove the pipeline mechanics (segmentation converges, mesh is watertight,
metrics are computed correctly) independent of having real data on hand.
"""

from __future__ import annotations

import math
import os

import numpy as np
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_CT_PATH = os.path.join(REPO_ROOT, "data", "volumes", "CTChest.nrrd")


@pytest.fixture
def real_ct_path() -> str:
    if not os.path.exists(REAL_CT_PATH):
        pytest.skip(f"Real CT fixture not found at {REAL_CT_PATH}")
    return REAL_CT_PATH


@pytest.fixture
def sphere_volume():
    """A sphere of known radius, offset from the volume corner, so the mesh
    metrics test can check computed volume/surface-area/centroid against
    closed-form geometry.
    """
    from medical3d.core.volume import Volume

    shape = (80, 80, 80)  # (z, y, x)
    spacing = (1.0, 1.0, 1.0)
    center_zyx = (40, 42, 38)
    radius = 20.0

    zz, yy, xx = np.meshgrid(*(np.arange(s) for s in shape), indexing="ij")
    mask = (zz - center_zyx[0]) ** 2 + (yy - center_zyx[1]) ** 2 + (xx - center_zyx[2]) ** 2 <= radius**2

    array = np.zeros(shape, dtype=np.float32)
    volume = Volume(
        array=array, spacing=spacing, origin=(0.0, 0.0, 0.0), direction=(1, 0, 0, 0, 1, 0, 0, 0, 1),
        modality="CT", source_path="synthetic-sphere",
    )
    expected_volume_mm3 = 4.0 / 3.0 * math.pi * radius**3
    expected_surface_area_mm2 = 4.0 * math.pi * radius**2
    expected_center_xyz = (float(center_zyx[2]), float(center_zyx[1]), float(center_zyx[0]))
    return mask, volume, expected_volume_mm3, expected_surface_area_mm2, expected_center_xyz


@pytest.fixture
def liver_phantom_volume():
    from medical3d.core.volume import Volume

    rng = np.random.default_rng(0)
    shape = (200, 300, 300)  # (z, y, x)
    spacing = (1.0, 1.0, 1.0)
    array = np.full(shape, -1000.0, dtype=np.float32)

    zz, yy, xx = np.meshgrid(*(np.arange(s) for s in shape), indexing="ij")
    body = ((yy - 150) ** 2 / 140.0**2 + (xx - 150) ** 2 / 140.0**2) < 1.0
    array[body] = -50.0

    liver_center = (100, 100, 90)  # (z, y, x); low x = patient right in this ROI convention
    liver = (
        ((zz - liver_center[0]) / 45.0) ** 2
        + ((yy - liver_center[1]) / 55.0) ** 2
        + ((xx - liver_center[2]) / 55.0) ** 2
    ) < 1.0
    liver = liver & body
    array[liver] = 50.0

    array += rng.normal(0.0, 15.0, size=array.shape).astype(np.float32)

    expected_liver_volume_mm3 = 4.0 / 3.0 * math.pi * 45.0 * 55.0 * 55.0

    volume = Volume(
        array=array, spacing=spacing, origin=(0.0, 0.0, 0.0), direction=(1, 0, 0, 0, 1, 0, 0, 0, 1),
        modality="CT", source_path="synthetic-liver",
    )
    return volume, expected_liver_volume_mm3


@pytest.fixture
def kidneys_phantom_volume():
    from medical3d.core.volume import Volume

    rng = np.random.default_rng(0)
    shape = (120, 200, 300)  # (z, y, x)
    spacing = (1.0, 1.0, 1.0)
    array = np.full(shape, -1000.0, dtype=np.float32)

    zz, yy, xx = np.meshgrid(*(np.arange(s) for s in shape), indexing="ij")
    body = ((yy - 100) ** 2 / 95.0**2 + (xx - 150) ** 2 / 145.0**2) < 1.0
    array[body] = -50.0

    right_center = (60, 140, 90)
    left_center = (60, 140, 210)
    right_kidney = (
        ((zz - right_center[0]) / 25.0) ** 2
        + ((yy - right_center[1]) / 35.0) ** 2
        + ((xx - right_center[2]) / 20.0) ** 2
    ) < 1.0
    left_kidney = (
        ((zz - left_center[0]) / 25.0) ** 2
        + ((yy - left_center[1]) / 35.0) ** 2
        + ((xx - left_center[2]) / 20.0) ** 2
    ) < 1.0
    kidneys = (right_kidney | left_kidney) & body
    array[kidneys] = 40.0

    array += rng.normal(0.0, 15.0, size=array.shape).astype(np.float32)

    expected_each_kidney_volume_mm3 = 4.0 / 3.0 * math.pi * 25.0 * 35.0 * 20.0

    volume = Volume(
        array=array, spacing=spacing, origin=(0.0, 0.0, 0.0), direction=(1, 0, 0, 0, 1, 0, 0, 0, 1),
        modality="CT", source_path="synthetic-kidneys",
    )
    return volume, 2 * expected_each_kidney_volume_mm3
