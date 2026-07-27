"""Shared test fixtures: synthetic phantoms and the real CT fixture.

Liver and kidney pipelines are validated here against synthetic phantoms
rather than real abdominal CT, because the only real scan committed to
this repository (``data/volumes/CTChest.nrrd``) is a chest CT and does not
include the abdomen. The phantoms are not a substitute for validation
against expert-labeled clinical data (see docs/VALIDATION.md) — they exist
to prove the pipeline mechanics (segmentation converges, mesh is watertight,
metrics are computed correctly) independent of having real data on hand.

The liver and kidney phantom shapes are built from unions/subtractions of
ellipsoids (a tapered two-lobe wedge for the liver, an ellipsoid with a
medial concave notch for each kidney) rather than a single plain ellipsoid,
so the reconstructed mesh is recognizably organ-shaped rather than an egg —
plain ellipsoids exercised the segmentation logic just as well but made
generated previews (and any human looking at one) unable to tell liver from
kidney from a lightbulb. The phantom-building functions are plain (non-
fixture) so other tooling — e.g. a demo/preview script — can reuse the exact
same shapes rather than re-deriving a slightly different approximation.
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


def _ellipsoid_mask(shape_zyx, center_zyx, radii_zyx) -> np.ndarray:
    zz, yy, xx = np.meshgrid(*(np.arange(s) for s in shape_zyx), indexing="ij")
    cz, cy, cx = center_zyx
    rz, ry, rx = radii_zyx
    return ((zz - cz) / rz) ** 2 + ((yy - cy) / ry) ** 2 + ((xx - cx) / rx) ** 2 <= 1.0


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

    mask = _ellipsoid_mask(shape, center_zyx, (radius, radius, radius))

    array = np.zeros(shape, dtype=np.float32)
    volume = Volume(
        array=array, spacing=spacing, origin=(0.0, 0.0, 0.0), direction=(1, 0, 0, 0, 1, 0, 0, 0, 1),
        modality="CT", source_path="synthetic-sphere",
    )
    expected_volume_mm3 = 4.0 / 3.0 * math.pi * radius**3
    expected_surface_area_mm2 = 4.0 * math.pi * radius**2
    expected_center_xyz = (float(center_zyx[2]), float(center_zyx[1]), float(center_zyx[0]))
    return mask, volume, expected_volume_mm3, expected_surface_area_mm2, expected_center_xyz


def build_liver_phantom_mask(shape_zyx=(200, 300, 300)) -> np.ndarray:
    """A tapered two-lobe wedge: a large right lobe and a smaller, closely
    overlapping left lobe, with a shallow notch standing in for the
    gallbladder fossa / porta hepatis. Not derived from any real patient —
    a stylized approximation good enough to read as "liver-shaped" rather
    than "ellipsoid."
    """
    right_lobe = _ellipsoid_mask(shape_zyx, (100, 95, 75), (46, 54, 50))
    left_lobe = _ellipsoid_mask(shape_zyx, (102, 100, 112), (34, 42, 36))
    liver = right_lobe | left_lobe
    notch = _ellipsoid_mask(shape_zyx, (122, 78, 90), (16, 20, 22))
    return liver & ~notch


def build_kidney_pair_mask(shape_zyx=(120, 200, 300)):
    """Two bean-shaped (reniform) kidneys: an ellipsoid per side with a
    shallow concave notch carved out of its medial face (the hilum), each
    notch facing the midline so the two read as a mirrored pair.
    Returns (mask, right_center_zyx, left_center_zyx).
    """
    right_center = (60, 140, 90)
    right_kidney = _ellipsoid_mask(shape_zyx, right_center, (22, 32, 20))
    right_notch = _ellipsoid_mask(shape_zyx, (right_center[0], right_center[1], right_center[2] + 24), (16, 14, 13))
    right_kidney = right_kidney & ~right_notch

    left_center = (60, 140, 210)
    left_kidney = _ellipsoid_mask(shape_zyx, left_center, (22, 32, 20))
    left_notch = _ellipsoid_mask(shape_zyx, (left_center[0], left_center[1], left_center[2] - 24), (16, 14, 13))
    left_kidney = left_kidney & ~left_notch

    return (right_kidney | left_kidney), right_center, left_center


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

    liver = build_liver_phantom_mask(shape) & body
    array[liver] = 50.0

    array += rng.normal(0.0, 15.0, size=array.shape).astype(np.float32)

    # Ground truth is the actual voxel count of the constructed shape (it's
    # a boolean union/subtraction of ellipsoids, not a single closed form).
    expected_liver_volume_mm3 = float(liver.sum()) * (spacing[0] * spacing[1] * spacing[2])

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

    kidneys, _right_center, _left_center = build_kidney_pair_mask(shape)
    kidneys = kidneys & body
    array[kidneys] = 40.0

    array += rng.normal(0.0, 15.0, size=array.shape).astype(np.float32)

    expected_kidneys_volume_mm3 = float(kidneys.sum()) * (spacing[0] * spacing[1] * spacing[2])

    volume = Volume(
        array=array, spacing=spacing, origin=(0.0, 0.0, 0.0), direction=(1, 0, 0, 0, 1, 0, 0, 0, 1),
        modality="CT", source_path="synthetic-kidneys",
    )
    return volume, expected_kidneys_volume_mm3
