"""Heart segmentation: gradient-based geodesic active contour level set.

This is the boundary-aware approach the project's prior work identified as
necessary for the heart: instead of thresholding intensity (which overlaps
with the aorta, vena cava, pericardial fat, and diaphragm), a level set
front is seeded inside the heart and evolves outward, slowed to a stop by
a speed function derived from the local image *gradient* — i.e. it stops
at edges, not at an intensity value.

Steps:
  1. Gradient magnitude of the (denoised) ROI.
  2. Sigmoid-map the gradient to a [0, 1] speed image: near 1 in
     homogeneous interior regions, near 0 at strong edges.
  3. Auto-seed at the centroid of soft-tissue-range voxels in the ROI
     (heart blood pool / myocardium HU), then build a spherical signed
     distance function around it as the initial contour.
  4. Evolve with ``GeodesicActiveContourLevelSetImageFilter``; threshold
     the result at 0 for the final binary mask.
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

    seed = _auto_seed(volume.array, config.get("seed_hu_range", [-30, 100]))
    init_level_set = _spherical_level_set(
        volume, seed, radius_mm=config.get("initial_sphere_radius_mm", 15.0)
    )

    gac = sitk.GeodesicActiveContourLevelSetImageFilter()
    gac.SetPropagationScaling(config.get("propagation_scaling", 0.6))
    gac.SetCurvatureScaling(config.get("curvature_scaling", 1.2))
    gac.SetAdvectionScaling(config.get("advection_scaling", 1.5))
    gac.SetMaximumRMSError(config.get("max_rms_error", 0.005))
    gac.SetNumberOfIterations(config.get("max_iterations", 500))

    init_image = sitk.GetImageFromArray(init_level_set.astype(np.float32))
    init_image.CopyInformation(image)

    result = gac.Execute(init_image, sitk.Cast(speed, sitk.sitkFloat32))
    result_arr = sitk.GetArrayFromImage(result)

    return result_arr < 0


def _auto_seed(array: np.ndarray, hu_range: list[float]) -> tuple[int, int, int]:
    """Centroid (z, y, x) of voxels within the expected heart HU range."""
    low, high = hu_range
    candidate = (array > low) & (array < high)
    if not candidate.any():
        # Fall back to the geometric center of the ROI.
        return tuple(s // 2 for s in array.shape)
    zz, yy, xx = np.nonzero(candidate)
    return int(zz.mean()), int(yy.mean()), int(xx.mean())


def _spherical_level_set(volume: Volume, seed_zyx: tuple[int, int, int], radius_mm: float) -> np.ndarray:
    """Signed distance (mm) from ``seed_zyx`` minus ``radius_mm``: negative
    inside the sphere, positive outside — the sign convention
    ``GeodesicActiveContourLevelSetImageFilter`` expects for its initial front.
    """
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
