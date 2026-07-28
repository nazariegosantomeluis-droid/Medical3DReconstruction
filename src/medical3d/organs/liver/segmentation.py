"""Liver segmentation.

**CT** (clinical, in-vivo, ``_segment_ct``): seeded confidence-connected
region growing. Liver parenchyma is intensity-homogeneous but not
intensity-*unique* (it overlaps with spleen, kidney, and muscle HU), so the
right primitive is region growing from a point known to be inside the
liver, not a global threshold. ``ConfidenceConnected`` grows the region as
long as neighboring voxels stay within ``multiplier`` standard deviations
of the current region's mean, re-estimating that statistic at each
iteration — this adapts to the liver's real (mild) internal intensity
variation in a way a fixed threshold band cannot, which is what let this
approach reach Dice 0.918 in prior project work.

**synchrotron** (ex-vivo tomography, ``_segment_synchrotron``): a plain
intensity threshold + largest-connected-component, the same rationale as
``organs/heart/segmentation.py``'s synchrotron branch — ex-vivo
phase-contrast tomography separates tissue from the mounting medium by
intensity alone once downsampled, so region growing's adaptive machinery
is unnecessary.
"""

from __future__ import annotations

import numpy as np
import SimpleITK as sitk
from scipy import ndimage

from medical3d.core.config import OrganConfig
from medical3d.core.preprocessing_utils import largest_connected_components
from medical3d.core.volume import Volume


def segment(volume: Volume, config: OrganConfig) -> np.ndarray:
    if volume.modality == "synchrotron":
        return _segment_synchrotron(volume, config)
    return _segment_ct(volume, config)


def _segment_synchrotron(volume: Volume, config: OrganConfig) -> np.ndarray:
    threshold = config.get("tissue_intensity_threshold", 18300)
    tissue = volume.array > threshold
    opened = ndimage.binary_opening(tissue, structure=np.ones((3, 3, 3)))
    return largest_connected_components(opened, n=1, min_voxels=1)


def _segment_ct(volume: Volume, config: OrganConfig) -> np.ndarray:
    image = volume.to_sitk_image()

    seed = _auto_seed(volume.array, config.get("seed_hu_range", [20, 70]))

    region_growing = sitk.ConfidenceConnectedImageFilter()
    region_growing.SetSeedList([(int(seed[2]), int(seed[1]), int(seed[0]))])  # sitk index order (x, y, z)
    region_growing.SetMultiplier(config.get("confidence_multiplier", 2.5))
    region_growing.SetNumberOfIterations(config.get("confidence_iterations", 5))
    region_growing.SetInitialNeighborhoodRadius(config.get("confidence_initial_neighborhood_radius", 2))
    region_growing.SetReplaceValue(1)

    result = region_growing.Execute(image)
    return sitk.GetArrayFromImage(result).astype(bool)


def _auto_seed(array: np.ndarray, hu_range: list[float]) -> tuple[int, int, int]:
    """Centroid (z, y, x) of voxels within the expected liver HU range,
    inside the already-cropped right-upper-quadrant ROI.
    """
    low, high = hu_range
    candidate = (array > low) & (array < high)
    if not candidate.any():
        return tuple(s // 2 for s in array.shape)
    zz, yy, xx = np.nonzero(candidate)
    return int(zz.mean()), int(yy.mean()), int(xx.mean())
