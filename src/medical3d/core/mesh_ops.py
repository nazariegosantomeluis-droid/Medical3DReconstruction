"""Mesh optimization: smoothing, decimation, and watertight repair.

These operate on the geometry only (no image/intensity data), so they are
shared across organs — every organ pipeline calls them with its own
parameters after generating its own mesh from its own segmentation.
"""

from __future__ import annotations

from dataclasses import dataclass

import trimesh
from trimesh.smoothing import filter_taubin


@dataclass(frozen=True)
class MeshQualityReport:
    is_watertight: bool
    is_winding_consistent: bool
    euler_number: int
    num_bodies: int


def smooth_mesh(mesh: trimesh.Trimesh, iterations: int = 10, lamb: float = 0.5, nu: float = 0.53) -> trimesh.Trimesh:
    """Taubin (lambda/mu) smoothing: reduces marching-cubes staircase noise
    without the shrinkage a plain Laplacian filter would introduce.
    """
    smoothed = mesh.copy()
    if len(smoothed.faces) == 0:
        return smoothed
    filter_taubin(smoothed, lamb=lamb, nu=nu, iterations=iterations)
    return smoothed


def decimate_mesh(mesh: trimesh.Trimesh, target_face_fraction: float = 0.5) -> trimesh.Trimesh:
    """Reduce triangle count via quadric edge-collapse decimation.

    Args:
        target_face_fraction: Fraction of the original face count to keep,
            in ``(0, 1]``. ``1.0`` is a no-op.
    """
    if not (0 < target_face_fraction <= 1.0):
        raise ValueError(f"target_face_fraction must be in (0, 1], got {target_face_fraction}")
    if target_face_fraction >= 1.0 or len(mesh.faces) == 0:
        return mesh.copy()
    target_faces = max(4, int(len(mesh.faces) * target_face_fraction))
    return mesh.simplify_quadric_decimation(face_count=target_faces)


def remove_small_components(mesh: trimesh.Trimesh, min_volume_fraction: float = 0.01) -> trimesh.Trimesh:
    """Drop connected mesh components smaller than ``min_volume_fraction`` of
    the largest one.

    Marching cubes + smoothing can leave a handful of near-degenerate
    fragments (a few dozen triangles from a single stray voxel survived by
    morphological postprocessing) alongside the real anatomy. This keeps
    legitimately separate large structures — both lungs, both kidneys — while
    discarding noise, because the filter is relative to the largest body
    rather than an absolute component count.
    """
    if len(mesh.faces) == 0:
        return mesh.copy()
    bodies = mesh.split(only_watertight=False)
    if len(bodies) <= 1:
        return mesh.copy()

    volumes = [abs(body.volume) if body.is_watertight else body.area for body in bodies]
    largest = max(volumes)
    if largest <= 0:
        return mesh.copy()

    kept = [body for body, vol in zip(bodies, volumes) if vol >= min_volume_fraction * largest]
    if not kept:
        return mesh.copy()
    return trimesh.util.concatenate(kept)


def repair_mesh(mesh: trimesh.Trimesh, min_volume_fraction: float = 0.01) -> trimesh.Trimesh:
    """Best-effort repair to a clean, watertight, consistently-wound mesh."""
    repaired = mesh.copy()
    if len(repaired.faces) == 0:
        return repaired
    repaired.merge_vertices()
    repaired.update_faces(repaired.unique_faces())
    repaired.update_faces(repaired.nondegenerate_faces())
    repaired.remove_unreferenced_vertices()
    trimesh.repair.fill_holes(repaired)
    trimesh.repair.fix_normals(repaired, multibody=True)
    repaired = remove_small_components(repaired, min_volume_fraction=min_volume_fraction)
    return repaired


def assess_mesh_quality(mesh: trimesh.Trimesh) -> MeshQualityReport:
    return MeshQualityReport(
        is_watertight=bool(mesh.is_watertight),
        is_winding_consistent=bool(mesh.is_winding_consistent),
        euler_number=int(mesh.euler_number),
        num_bodies=int(mesh.body_count),
    )
