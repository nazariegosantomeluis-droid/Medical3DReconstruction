"""Heart segmentation.

Two independent algorithms, chosen by acquisition modality — this is the
same architectural point as the preprocessing split (see
``preprocessing.py``): the physics of the acquisition determines what's
possible, not just what's convenient.

**CT** (clinical, in-vivo, ``segment_ct``): gradient-based geodesic active
contour level set. Myocardium/blood pool HU overlaps the aorta, vena cava,
pericardial fat, and diaphragm, so a level set seeded inside the heart and
evolved outward, slowed to a stop by a speed function derived from the
local image *gradient*, is used instead of thresholding intensity — it
stops at edges, not at an intensity value.

**synchrotron** (ex-vivo tomography, ``segment_synchrotron``): a plain
intensity threshold + largest-connected-component. Ex-vivo phase-contrast
tomography gives dramatically higher soft-tissue contrast than clinical
CT — tissue and the surrounding mounting medium are already well
separated in intensity once the sample-holder tube is excluded
geometrically (done in preprocessing) — so the boundary-aware machinery
CT needs would be solving a problem that, for this modality, doesn't exist.
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
    threshold = config.get("tissue_intensity_threshold", 27000)
    tissue = volume.array > threshold

    # A few voxels of morphological opening removes the salt-noise speckle
    # inherent to phase-contrast tomography (and the mounting medium's
    # texture) without eroding real tissue, which is many voxels thick at
    # this resolution.
    opened = ndimage.binary_opening(tissue, structure=np.ones((3, 3, 3)))

    return largest_connected_components(opened, n=1, min_voxels=1)


def _segment_ct(volume: Volume, config: OrganConfig) -> np.ndarray:
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
