"""Lung postprocessing: hole filling + morphological closing.

Hole filling recovers vessels/nodules interior to the lung field that were
excluded by the intensity threshold (they are soft-tissue density, not air).
Closing smooths the pleural surface and reincorporates juxtapleural
structures that a pure threshold would nick off the boundary.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage

from medical3d.core.config import OrganConfig
from medical3d.core.preprocessing_utils import fill_holes_3d, largest_connected_components
from medical3d.core.volume import Volume


def postprocess(mask: np.ndarray, volume: Volume, config: OrganConfig) -> np.ndarray:
    filled = fill_holes_3d(mask)

    radius_mm = config.get("morphological_closing_radius_mm", 2.0)
    if radius_mm > 0:
        voxel_radius = max(1, int(round(radius_mm / min(volume.spacing))))
        structure = _ball(voxel_radius)
        filled = ndimage.binary_closing(filled, structure=structure)
        filled = fill_holes_3d(filled)

    # Closing can introduce a handful of tiny disconnected islands; strip
    # anything outside the expected component count (left + right lung).
    num_components = config.get("num_components", 2)
    min_voxels = config.get("min_component_voxels", 1500)
    filled = largest_connected_components(filled, n=num_components, min_voxels=min_voxels)

    return filled


def _ball(radius: int) -> np.ndarray:
    grid = np.arange(-radius, radius + 1)
    zz, yy, xx = np.meshgrid(grid, grid, grid, indexing="ij")
    return (zz**2 + yy**2 + xx**2) <= radius**2
