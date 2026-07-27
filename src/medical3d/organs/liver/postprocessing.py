"""Liver postprocessing: largest component, hole filling, morphological closing."""

from __future__ import annotations

import numpy as np
from scipy import ndimage

from medical3d.core.config import OrganConfig
from medical3d.core.preprocessing_utils import fill_holes_3d, largest_connected_components
from medical3d.core.volume import Volume


def postprocess(mask: np.ndarray, volume: Volume, config: OrganConfig) -> np.ndarray:
    cleaned = largest_connected_components(mask, n=1, min_voxels=1)
    cleaned = fill_holes_3d(cleaned)

    radius_mm = config.get("morphological_closing_radius_mm", 2.0)
    if radius_mm > 0:
        voxel_radius = max(1, int(round(radius_mm / min(volume.spacing))))
        structure = _ball(voxel_radius)
        cleaned = ndimage.binary_closing(cleaned, structure=structure)
        cleaned = fill_holes_3d(cleaned)

    return cleaned


def _ball(radius: int) -> np.ndarray:
    grid = np.arange(-radius, radius + 1)
    zz, yy, xx = np.meshgrid(grid, grid, grid, indexing="ij")
    return (zz**2 + yy**2 + xx**2) <= radius**2
