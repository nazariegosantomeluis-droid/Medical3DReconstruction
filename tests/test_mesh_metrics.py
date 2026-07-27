"""Mesh generation and metrics correctness, checked against closed-form geometry."""

from __future__ import annotations

import numpy as np
import pytest

from medical3d.core.mesh import compute_mesh_metrics, mask_to_mesh


def test_sphere_volume_and_surface_area(sphere_volume):
    mask, volume, expected_volume_mm3, expected_surface_area_mm2, _expected_center = sphere_volume

    mesh = mask_to_mesh(mask, volume, smoothing_sigma=0.5)
    metrics = compute_mesh_metrics(mesh)

    # Marching cubes on a voxelized sphere is a discrete approximation, not
    # exact — tolerances are wide enough to catch a broken axis mapping or
    # a unit error (mm vs voxels) but tight enough to fail on a geometry bug.
    assert metrics.volume_mm3 == pytest.approx(expected_volume_mm3, rel=0.05)
    assert metrics.surface_area_mm2 == pytest.approx(expected_surface_area_mm2, rel=0.08)


def test_sphere_centroid_matches_known_offset(sphere_volume):
    mask, volume, _expected_volume, _expected_area, expected_center_xyz = sphere_volume

    mesh = mask_to_mesh(mask, volume, smoothing_sigma=0.5)
    metrics = compute_mesh_metrics(mesh)

    for computed, expected in zip(metrics.centroid_mm, expected_center_xyz):
        assert computed == pytest.approx(expected, abs=1.0)


def test_sphere_bounding_box_and_counts(sphere_volume):
    mask, volume, _v, _a, _c = sphere_volume

    mesh = mask_to_mesh(mask, volume, smoothing_sigma=0.5)
    metrics = compute_mesh_metrics(mesh)

    diag = np.array(metrics.bounding_box_max_mm) - np.array(metrics.bounding_box_min_mm)
    assert np.all(diag > 0)
    assert np.all(diag < 45)  # sphere radius 20 -> diameter 40, plus a small margin

    assert metrics.num_vertices > 0
    assert metrics.num_triangles > 0
    assert metrics.num_triangles == len(mesh.faces)


def test_mask_to_mesh_rejects_empty_mask(sphere_volume):
    _mask, volume, _v, _a, _c = sphere_volume
    empty_mask = np.zeros(volume.array.shape, dtype=bool)

    with pytest.raises(ValueError):
        mask_to_mesh(empty_mask, volume)


def test_mask_to_mesh_rejects_shape_mismatch(sphere_volume):
    mask, volume, _v, _a, _c = sphere_volume
    wrong_shape_mask = mask[:-1]

    with pytest.raises(ValueError):
        mask_to_mesh(wrong_shape_mask, volume)


def test_mesh_normals_point_outward(sphere_volume):
    """A watertight sphere mesh with outward normals should report a
    positive signed volume via trimesh's own convention once normals are
    fixed — this is the check that would fail if the world-space axis
    reordering in mask_to_mesh silently mirrored the geometry.
    """
    mask, volume, _v, _a, _c = sphere_volume
    mesh = mask_to_mesh(mask, volume, smoothing_sigma=0.5)

    assert mesh.is_winding_consistent
    assert mesh.volume > 0
