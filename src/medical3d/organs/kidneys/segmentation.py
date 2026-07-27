"""Kidney segmentation: bilateral gradient-based geodesic active contour level set.

Kidneys need the same *class* of technique as the heart (boundary-aware,
because renal parenchyma HU overlaps the psoas muscle and adjacent organs)
but the segmentation problem itself is different: there are two objects,
found independently in the left and right halves of a shared ROI, each
with its own seed. This module is deliberately self-contained rather than
importing the heart pipeline's level-set code — the two organs' pipelines
are independent by design (see AUDIT.md / docs/ARCHITECTURE.md), each
implementing the algorithm it needs rather than sharing a segmentation
routine parameterized by organ name.
"""

from __future__ import annotations

import numpy as np
import SimpleITK as sitk

from medical3d.core.config import OrganConfig
from medical3d.core.volume import Volume


def segment(volume: Volume, config: OrganConfig) -> np.ndarray:
    image = volume.to_sitk_image()

    gradient_sigma = config.get("gradient_sigma_mm", 1.0)
    gradient = sitk.GradientMagnitudeRecursiveGaussian(image, sigma=gradient_sigma)
    gradient_arr = sitk.GetArrayFromImage(gradient)

    beta = float(np.percentile(gradient_arr, 90))
    alpha = -0.25 * beta
    speed = sitk.Sigmoid(gradient, alpha=alpha, beta=beta, outputMaximum=1.0, outputMinimum=0.0)
    speed_cast = sitk.Cast(speed, sitk.sitkFloat32)

    hu_range = config.get("seed_hu_range", [20, 70])
    left_seed, right_seed = _bilateral_seeds(volume.array, hu_range)

    radius_mm = config.get("initial_sphere_radius_mm", 8.0)
    combined_mask = np.zeros(volume.array.shape, dtype=bool)

    for seed in (left_seed, right_seed):
        if seed is None:
            continue
        init_level_set = _spherical_level_set(volume, seed, radius_mm)
        init_image = sitk.GetImageFromArray(init_level_set.astype(np.float32))
        init_image.CopyInformation(image)

        gac = sitk.GeodesicActiveContourLevelSetImageFilter()
        gac.SetPropagationScaling(config.get("propagation_scaling", 0.6))
        gac.SetCurvatureScaling(config.get("curvature_scaling", 1.2))
        gac.SetAdvectionScaling(config.get("advection_scaling", 1.5))
        gac.SetMaximumRMSError(config.get("max_rms_error", 0.005))
        gac.SetNumberOfIterations(config.get("max_iterations", 500))

        result = gac.Execute(init_image, speed_cast)
        combined_mask |= sitk.GetArrayFromImage(result) < 0

    return combined_mask


def _bilateral_seeds(
    array: np.ndarray, hu_range: list[float]
) -> tuple[tuple[int, int, int] | None, tuple[int, int, int] | None]:
    """Centroid seeds for the left and right halves of the (already cropped,
    bilateral) ROI, restricted to the expected renal-parenchyma HU range.
    """
    low, high = hu_range
    candidate = (array > low) & (array < high)

    nz, ny, nx = array.shape
    midpoint = nx // 2

    left_candidate = candidate.copy()
    left_candidate[:, :, midpoint:] = False
    right_candidate = candidate.copy()
    right_candidate[:, :, :midpoint] = False

    return _centroid_or_none(left_candidate), _centroid_or_none(right_candidate)


def _centroid_or_none(mask: np.ndarray) -> tuple[int, int, int] | None:
    if not mask.any():
        return None
    zz, yy, xx = np.nonzero(mask)
    return int(zz.mean()), int(yy.mean()), int(xx.mean())


def _spherical_level_set(volume: Volume, seed_zyx: tuple[int, int, int], radius_mm: float) -> np.ndarray:
    sx, sy, sz = volume.spacing
    nz, ny, nx = volume.array.shape
    zz, yy, xx = np.meshgrid(
        (np.arange(nz) - seed_zyx[0]) * sz,
        (np.arange(ny) - seed_zyx[1]) * sy,
        (np.arange(nx) - seed_zyx[2]) * sx,
        indexing="ij",
    )
    distance = np.sqrt(zz**2 + yy**2 + xx**2)
    return distance - radius_mm
