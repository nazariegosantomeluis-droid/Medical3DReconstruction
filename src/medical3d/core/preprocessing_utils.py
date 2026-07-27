"""Generic, organ-agnostic image operations (resampling, denoising, windowing).

These are library-grade primitives, not segmentation algorithms — every
organ's ``preprocessing.py`` composes them differently and adds its own
anatomical ROI priors, which is where the actual organ-specific logic lives.
"""

from __future__ import annotations

import numpy as np
import SimpleITK as sitk

from medical3d.core.volume import Volume


def resample_to_isotropic(volume: Volume, target_spacing_mm: float | None = None) -> Volume:
    """Resample to isotropic voxel spacing so the reconstructed mesh isn't
    stretched along the (usually coarser) slice axis.

    If ``target_spacing_mm`` is omitted, the smallest in-plane spacing is
    used (never upsamples above native in-plane resolution).
    """
    image = volume.to_sitk_image()
    sx, sy, sz = volume.spacing
    spacing = target_spacing_mm if target_spacing_mm is not None else min(sx, sy)

    original_size = image.GetSize()
    new_size = [
        max(1, int(round(original_size[i] * volume.spacing[i] / spacing))) for i in range(3)
    ]

    resampler = sitk.ResampleImageFilter()
    resampler.SetOutputSpacing((spacing, spacing, spacing))
    resampler.SetSize(new_size)
    resampler.SetOutputOrigin(image.GetOrigin())
    resampler.SetOutputDirection(image.GetDirection())
    resampler.SetInterpolator(sitk.sitkLinear)
    resampler.SetDefaultPixelValue(float(np.min(volume.array)))
    resampled = resampler.Execute(image)

    return Volume.from_sitk_image(resampled, modality=volume.modality, source_path=volume.source_path)


def gaussian_denoise(volume: Volume, sigma_mm: float = 0.8) -> Volume:
    """Edge-preserving-ish smoothing to reduce acquisition noise before thresholding."""
    if sigma_mm <= 0:
        return volume
    image = volume.to_sitk_image()
    smoothed = sitk.SmoothingRecursiveGaussian(image, sigma=sigma_mm)
    return volume.with_array(sitk.GetArrayFromImage(smoothed).astype(np.float32))


def window_intensity(volume: Volume, low: float, high: float) -> Volume:
    """Clip intensities to ``[low, high]``. For CT this is an HU window
    (e.g. a soft-tissue or lung window); for MRI, a raw-intensity clip.
    """
    clipped = np.clip(volume.array, low, high)
    return volume.with_array(clipped.astype(np.float32))


def largest_connected_components(mask: np.ndarray, n: int = 1, min_voxels: int = 1) -> np.ndarray:
    """Keep the ``n`` largest connected components (26-connectivity) of a binary mask."""
    from scipy import ndimage

    labeled, num_features = ndimage.label(mask, structure=np.ones((3, 3, 3)))
    if num_features == 0:
        return np.zeros_like(mask, dtype=bool)

    sizes = ndimage.sum(mask, labeled, index=range(1, num_features + 1))
    ranked = sorted(
        ((size, idx + 1) for idx, size in enumerate(sizes) if size >= min_voxels),
        reverse=True,
    )
    keep_labels = {idx for _size, idx in ranked[:n]}

    out = np.isin(labeled, list(keep_labels)) if keep_labels else np.zeros_like(mask, dtype=bool)
    return out


def fill_holes_3d(mask: np.ndarray) -> np.ndarray:
    from scipy import ndimage

    return ndimage.binary_fill_holes(mask)


def crop_fractional_roi(
    volume: Volume,
    x_fraction: tuple[float, float],
    y_fraction: tuple[float, float],
    z_fraction: tuple[float, float],
) -> Volume:
    """Crop to a region of interest expressed as fractions ``(0, 1]`` of the
    full volume's extent along each axis. This is the mechanism every
    organ's ROI prior is implemented with; the fractions themselves are the
    organ-specific anatomical knowledge, supplied by each organ's config.
    """
    nz, ny, nx = volume.array.shape
    x0, x1 = int(x_fraction[0] * nx), int(x_fraction[1] * nx)
    y0, y1 = int(y_fraction[0] * ny), int(y_fraction[1] * ny)
    z0, z1 = int(z_fraction[0] * nz), int(z_fraction[1] * nz)

    cropped = volume.array[z0:z1, y0:y1, x0:x1].copy()
    new_origin = volume.index_to_world(np.array([[x0, y0, z0]], dtype=np.float64))[0]

    return Volume(
        array=cropped,
        spacing=volume.spacing,
        origin=tuple(new_origin),
        direction=volume.direction,
        modality=volume.modality,
        source_path=volume.source_path,
    )
