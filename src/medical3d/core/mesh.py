"""Mesh generation from a segmentation mask, and the metrics the spec requires.

Coordinate handling is the one place in this codebase where a small mistake
silently produces a plausible-looking but wrong (mirrored, squashed, or
misplaced) organ. The convention used everywhere below:

  * ``mask``/``Volume.array`` axes are ``(z, y, x)`` — SimpleITK/NumPy order.
  * ``skimage.measure.marching_cubes`` is run directly on that array, so its
    output vertices are also in ``(z, y, x)`` voxel-index order.
  * We reorder to ``(x, y, z)`` and apply ``Volume.index_to_world`` (which
    encodes spacing, origin and direction) to get true patient-physical
    millimeter coordinates.
  * Re-ordering axes is a reflection (an odd permutation), so after the
    transform the mesh may have inward-facing normals even though the
    surface itself is geometrically correct. ``trimesh.repair.fix_normals``
    is run unconditionally to guarantee outward-facing normals regardless
    of the sign of the acquisition's direction cosine matrix — this is what
    makes the organ render lit correctly instead of coming out matte-black
    ("inside out") in the 3D viewer.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import trimesh
from scipy import ndimage
from skimage import measure

from medical3d.core.volume import Volume


@dataclass(frozen=True)
class MeshMetrics:
    """The exact set of quantities the spec requires be computed."""

    volume_mm3: float
    surface_area_mm2: float
    centroid_mm: tuple[float, float, float]
    bounding_box_min_mm: tuple[float, float, float]
    bounding_box_max_mm: tuple[float, float, float]
    num_vertices: int
    num_triangles: int

    @property
    def volume_ml(self) -> float:
        """Volume in milliliters (cm^3) — the unit clinicians actually read."""
        return self.volume_mm3 / 1000.0

    def as_dict(self) -> dict:
        return {
            "volume_mm3": self.volume_mm3,
            "volume_ml": self.volume_ml,
            "surface_area_mm2": self.surface_area_mm2,
            "centroid_mm": self.centroid_mm,
            "bounding_box_min_mm": self.bounding_box_min_mm,
            "bounding_box_max_mm": self.bounding_box_max_mm,
            "num_vertices": self.num_vertices,
            "num_triangles": self.num_triangles,
        }


def mask_to_mesh(
    mask: np.ndarray,
    volume: Volume,
    smoothing_sigma: float = 1.0,
    level: float = 0.5,
) -> trimesh.Trimesh:
    """Generate a watertight-oriented surface mesh from a binary segmentation mask.

    Args:
        mask: Binary array, same shape as ``volume.array``, i.e. ``(z, y, x)``.
        volume: Source volume, supplying spacing/origin/direction so the mesh
            lands in correct physical millimeter coordinates.
        smoothing_sigma: Gaussian smoothing (in voxels) applied to the mask
            before marching cubes. Segmentation masks are binary/staircased;
            smoothing the implicit surface before extraction is standard
            practice for a mesh that isn't visibly voxelated. 0 disables it.
        level: Iso-surface level passed to marching cubes (0.5 is the
            natural threshold for a smoothed binary mask).

    Raises:
        ValueError: if the mask is empty (nothing to reconstruct).
    """
    if mask.shape != volume.array.shape:
        raise ValueError(f"Mask shape {mask.shape} does not match volume shape {volume.array.shape}")
    if not np.any(mask):
        raise ValueError("Cannot generate a mesh from an empty (all-zero) segmentation mask")

    field = mask.astype(np.float32)
    if smoothing_sigma > 0:
        field = ndimage.gaussian_filter(field, sigma=smoothing_sigma)
        if field.max() <= level:
            # Smoothing pulled the whole field below the iso-level (mask was
            # too small/thin relative to sigma); fall back to the raw mask.
            field = mask.astype(np.float32)

    sz, sy, sx = volume.spacing[2], volume.spacing[1], volume.spacing[0]
    verts_zyx, faces, _normals, _values = measure.marching_cubes(
        field, level=level, spacing=(sz, sy, sx)
    )

    # verts_zyx columns are (z_mm, y_mm, x_mm) local to the volume corner.
    # Convert to continuous voxel indices (x, y, z), then to world mm.
    local_xyz_mm = verts_zyx[:, ::-1]
    spacing_xyz = np.array(volume.spacing, dtype=np.float64)
    index_xyz = local_xyz_mm / spacing_xyz
    world_xyz = volume.index_to_world(index_xyz)

    mesh = trimesh.Trimesh(vertices=world_xyz, faces=faces, process=True)
    if len(mesh.faces) > 0:
        trimesh.repair.fix_normals(mesh, multibody=True)
    return mesh


def compute_mesh_metrics(mesh: trimesh.Trimesh) -> MeshMetrics:
    """Compute volume, surface area, centroid, bounding box, and vertex/triangle counts.

    Volume is computed from the mesh's signed tetrahedra decomposition
    (correct for a closed, consistently-oriented surface — which
    ``mask_to_mesh`` guarantees via ``fix_normals``), not by counting voxels,
    so it reflects the actual reconstructed geometry the user sees and exports.
    """
    bounds_min, bounds_max = mesh.bounds
    return MeshMetrics(
        volume_mm3=float(abs(mesh.volume)),
        surface_area_mm2=float(mesh.area),
        centroid_mm=tuple(float(c) for c in mesh.centroid),
        bounding_box_min_mm=tuple(float(v) for v in bounds_min),
        bounding_box_max_mm=tuple(float(v) for v in bounds_max),
        num_vertices=int(len(mesh.vertices)),
        num_triangles=int(len(mesh.faces)),
    )
