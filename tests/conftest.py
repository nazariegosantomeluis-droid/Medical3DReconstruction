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


@pytest.fixture
def synchrotron_heart_phantom_volume():
    """Stands in for a real ex-vivo synchrotron tomography scan (see
    configs/heart_synchrotron.yaml): a cylindrical sample-holder tube filled
    with a textured "mounting medium" background, and a denser tissue blob
    inside — same intensity relationships as the real LADAF-2021-17 data
    this pipeline branch was built and validated against (background
    ~24000-26000, tissue ~27000+), just a tiny synthetic volume instead of
    a ~150MB real one.
    """
    from medical3d.core.volume import Volume

    rng = np.random.default_rng(0)
    shape = (40, 80, 80)  # (z, y, x)
    spacing = (0.2, 0.2, 0.2)
    array = np.zeros(shape, dtype=np.float32)

    zz, yy, xx = np.meshgrid(*(np.arange(s) for s in shape), indexing="ij")
    cy, cx = 39.5, 39.5
    tube_radius = 37.0
    inside_tube = (yy - cy) ** 2 + (xx - cx) ** 2 <= tube_radius**2
    array[inside_tube] = 25000.0

    tissue = _ellipsoid_mask(shape, (20, 40, 40), (12, 22, 20)) & inside_tube
    array[tissue] = 29000.0

    array += rng.normal(0.0, 300.0, size=array.shape).astype(np.float32)
    array[~inside_tube] = 0.0

    expected_tissue_volume_mm3 = float(tissue.sum()) * (spacing[0] * spacing[1] * spacing[2])

    volume = Volume(
        array=array, spacing=spacing, origin=(0.0, 0.0, 0.0), direction=(1, 0, 0, 0, 1, 0, 0, 0, 1),
        modality="synchrotron", source_path="synthetic-heart-synchrotron",
    )
    return volume, expected_tissue_volume_mm3


@pytest.fixture
def synchrotron_brain_phantom_volume():
    """Stands in for a real ex-vivo synchrotron "complete-organ" brain scan
    (see configs/brain_synchrotron.yaml): unlike the heart/liver/kidney
    phantoms, tissue fills nearly the whole sample-holder tube — there is no
    separate low-density mounting medium to threshold away, just near-zero
    gaps/artifacts outside a high tissue population (real LADAF-2021-17
    brain data reads well above 3000 for tissue at the calibration slice).
    """
    from medical3d.core.volume import Volume

    rng = np.random.default_rng(1)
    shape = (40, 80, 80)  # (z, y, x)
    spacing = (0.2, 0.2, 0.2)
    array = np.zeros(shape, dtype=np.float32)

    yy, xx = np.meshgrid(np.arange(shape[1]), np.arange(shape[2]), indexing="ij")
    cy, cx = 39.5, 39.5
    tube_radius = 37.0
    inside_tube = (yy - cy) ** 2 + (xx - cx) ** 2 <= tube_radius**2

    tissue = _ellipsoid_mask(shape, (20, 40, 40), (18, 34, 34))
    tissue = tissue & np.broadcast_to(inside_tube, shape)
    array[tissue] = 4000.0

    array += rng.normal(0.0, 200.0, size=array.shape).astype(np.float32)
    array[~np.broadcast_to(inside_tube, shape)] = 0.0
    array[array < 0] = 0.0

    expected_tissue_volume_mm3 = float(tissue.sum()) * (spacing[0] * spacing[1] * spacing[2])

    volume = Volume(
        array=array, spacing=spacing, origin=(0.0, 0.0, 0.0), direction=(1, 0, 0, 0, 1, 0, 0, 0, 1),
        modality="synchrotron", source_path="synthetic-brain-synchrotron",
    )
    return volume, expected_tissue_volume_mm3


@pytest.fixture
def synchrotron_liver_phantom_volume():
    """Stands in for a real ex-vivo synchrotron liver scan (see
    configs/liver_synchrotron.yaml): unlike heart/brain, the real
    LADAF-2021-17 liver archive fills the frame with no sample-holder-tube
    margin visible, so this phantom has no tube-exclusion geometry either —
    just a mounting-medium background and a denser tissue blob (real data:
    background ~17200-18200, tissue ~19100-21000 native units).
    """
    from medical3d.core.volume import Volume

    rng = np.random.default_rng(2)
    shape = (40, 80, 80)  # (z, y, x)
    spacing = (0.2, 0.2, 0.2)
    array = np.full(shape, 17700.0, dtype=np.float32)

    tissue = _ellipsoid_mask(shape, (20, 40, 40), (14, 26, 24))
    array[tissue] = 20000.0

    array += rng.normal(0.0, 250.0, size=array.shape).astype(np.float32)

    expected_tissue_volume_mm3 = float(tissue.sum()) * (spacing[0] * spacing[1] * spacing[2])

    volume = Volume(
        array=array, spacing=spacing, origin=(0.0, 0.0, 0.0), direction=(1, 0, 0, 0, 1, 0, 0, 0, 1),
        modality="synchrotron", source_path="synthetic-liver-synchrotron",
    )
    return volume, expected_tissue_volume_mm3


@pytest.fixture
def synchrotron_kidneys_phantom_volume():
    """Stands in for a real ex-vivo synchrotron kidney scan (see
    configs/kidneys_synchrotron.yaml): the real K292 archive is a SINGLE
    excised kidney (not a bilateral pair), fills the frame with no tube
    margin visible, and reads much higher native intensity than the other
    archives (real data: background ~42600-43600, tissue ~43600-45600).
    """
    from medical3d.core.volume import Volume

    rng = np.random.default_rng(3)
    shape = (40, 80, 80)  # (z, y, x)
    spacing = (0.2, 0.2, 0.2)
    array = np.full(shape, 43100.0, dtype=np.float32)

    tissue = _ellipsoid_mask(shape, (20, 40, 40), (14, 26, 20))
    array[tissue] = 45000.0

    array += rng.normal(0.0, 250.0, size=array.shape).astype(np.float32)

    expected_tissue_volume_mm3 = float(tissue.sum()) * (spacing[0] * spacing[1] * spacing[2])

    volume = Volume(
        array=array, spacing=spacing, origin=(0.0, 0.0, 0.0), direction=(1, 0, 0, 0, 1, 0, 0, 0, 1),
        modality="synchrotron", source_path="synthetic-kidney-synchrotron",
    )
    return volume, expected_tissue_volume_mm3
