"""Physical-space volume representation shared by every organ pipeline.

A ``Volume`` wraps a SimpleITK image together with a NumPy view of its
voxel data and keeps spacing / origin / direction attached at all times.
Every downstream step (segmentation, mesh generation, visualization) reads
geometry from this object instead of re-deriving it, which is what keeps
mesh vertices in correct, reproducible patient-physical millimeters.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import SimpleITK as sitk


@dataclass(frozen=True)
class Volume:
    """An intensity volume plus the geometry needed to place it in physical space.

    Attributes:
        array: Voxel data with shape ``(nz, ny, nx)`` — SimpleITK/NumPy axis
            order — so ``array[k, j, i]`` is the voxel at index ``(i, j, k)``.
        spacing: Voxel spacing in millimeters, ``(sx, sy, sz)``.
        origin: Physical coordinate of voxel ``(0, 0, 0)``, ``(ox, oy, oz)``.
        direction: Row-major 3x3 direction cosine matrix mapping index space
            to physical space (identity for axis-aligned acquisitions).
        modality: ``"CT"`` or ``"MRI"``, as reported by DICOM metadata or the
            caller. Drives which intensity units (HU vs. arbitrary) organ
            pipelines assume.
        source_path: Where this volume was loaded from, kept for provenance
            in validation reports.
    """

    array: np.ndarray
    spacing: tuple[float, float, float]
    origin: tuple[float, float, float]
    direction: tuple[float, ...]
    modality: str
    source_path: str

    @classmethod
    def from_sitk_image(cls, image: sitk.Image, modality: str, source_path: str) -> "Volume":
        array = sitk.GetArrayFromImage(image).astype(np.float32)
        return cls(
            array=array,
            spacing=tuple(image.GetSpacing()),
            origin=tuple(image.GetOrigin()),
            direction=tuple(image.GetDirection()),
            modality=modality,
            source_path=source_path,
        )

    def to_sitk_image(self) -> sitk.Image:
        """Rebuild a SimpleITK image carrying this volume's geometry.

        Used whenever an ITK filter (region growing, watershed, level sets)
        needs a proper ``sitk.Image`` rather than a bare NumPy array.
        """
        image = sitk.GetImageFromArray(self.array)
        image.SetSpacing(self.spacing)
        image.SetOrigin(self.origin)
        image.SetDirection(self.direction)
        return image

    def with_array(self, array: np.ndarray) -> "Volume":
        """Return a copy of this volume with a new voxel array but identical geometry."""
        return Volume(
            array=array,
            spacing=self.spacing,
            origin=self.origin,
            direction=self.direction,
            modality=self.modality,
            source_path=self.source_path,
        )

    @property
    def shape_zyx(self) -> tuple[int, int, int]:
        return self.array.shape  # (nz, ny, nx)

    @property
    def direction_matrix(self) -> np.ndarray:
        return np.array(self.direction, dtype=np.float64).reshape(3, 3)

    @property
    def voxel_volume_mm3(self) -> float:
        sx, sy, sz = self.spacing
        return float(sx * sy * sz)

    def index_to_world(self, index_xyz: np.ndarray) -> np.ndarray:
        """Map an (N, 3) array of continuous voxel indices ``(ix, iy, iz)`` to
        physical millimeter coordinates, following the ITK convention:
        ``world = origin + D @ (spacing * index)``.
        """
        spacing_xyz = np.array(self.spacing, dtype=np.float64)
        scaled = index_xyz * spacing_xyz
        origin_xyz = np.array(self.origin, dtype=np.float64)
        return scaled @ self.direction_matrix.T + origin_xyz
