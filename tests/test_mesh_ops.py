"""Mesh smoothing, decimation, and repair."""

from __future__ import annotations

import trimesh

from medical3d.core.mesh_ops import (
    assess_mesh_quality,
    decimate_mesh,
    remove_small_components,
    repair_mesh,
    smooth_mesh,
)


def _icosphere_with_debris() -> trimesh.Trimesh:
    main = trimesh.creation.icosphere(subdivisions=3, radius=10.0)
    debris = trimesh.creation.icosphere(subdivisions=1, radius=0.2)
    debris.apply_translation([30.0, 30.0, 30.0])
    return trimesh.util.concatenate([main, debris])


def test_smooth_mesh_preserves_watertightness():
    mesh = trimesh.creation.icosphere(subdivisions=2, radius=10.0)
    smoothed = smooth_mesh(mesh, iterations=10)
    assert smoothed.is_watertight
    assert len(smoothed.vertices) == len(mesh.vertices)


def test_decimate_mesh_reduces_face_count():
    mesh = trimesh.creation.icosphere(subdivisions=4, radius=10.0)
    decimated = decimate_mesh(mesh, target_face_fraction=0.25)
    assert len(decimated.faces) < len(mesh.faces)
    assert len(decimated.faces) == _expected_face_count(mesh, 0.25)


def _expected_face_count(mesh: trimesh.Trimesh, fraction: float) -> int:
    return max(4, int(len(mesh.faces) * fraction))


def test_decimate_mesh_noop_at_full_fraction():
    mesh = trimesh.creation.icosphere(subdivisions=2, radius=10.0)
    same = decimate_mesh(mesh, target_face_fraction=1.0)
    assert len(same.faces) == len(mesh.faces)


def test_remove_small_components_drops_debris_keeps_large_body():
    mesh = _icosphere_with_debris()
    assert mesh.body_count == 2

    cleaned = remove_small_components(mesh, min_volume_fraction=0.01)
    assert cleaned.body_count == 1


def test_repair_mesh_yields_watertight_consistent_mesh():
    mesh = _icosphere_with_debris()
    repaired = repair_mesh(mesh)

    quality = assess_mesh_quality(repaired)
    assert quality.is_watertight
    assert quality.is_winding_consistent
    assert quality.num_bodies == 1
