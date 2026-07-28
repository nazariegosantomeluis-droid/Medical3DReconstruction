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
    """Keep the ``n`` largest connected components (26-connectivity) of a binary mask.

    Uses ``np.bincount`` rather than ``scipy.ndimage.sum`` with a per-label
    index to size components — for volumes with tens of thousands of noise
    components (real, high-resolution data is noisier than clinical CT),
    the latter is slow enough, and memory-heavy enough alongside the other
    large arrays already live at that point in a pipeline, to be a real
    problem rather than a style preference.
    """
    from scipy import ndimage

    labeled, num_features = ndimage.label(mask, structure=np.ones((3, 3, 3)))
    if num_features == 0:
        return np.zeros_like(mask, dtype=bool)

    sizes = np.bincount(labeled.ravel(), minlength=num_features + 1)
    sizes[0] = 0  # background label is never a candidate
    sizes[sizes < min_voxels] = 0

    keep_n = min(n, int(np.count_nonzero(sizes)))
    if keep_n == 0:
        return np.zeros_like(mask, dtype=bool)
    top_labels = np.argpartition(sizes, -keep_n)[-keep_n:]
    top_labels = top_labels[sizes[top_labels] > 0]

    return np.isin(labeled, top_labels)


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


def crop_to_mask_bbox(
    mask: np.ndarray,
    volume: Volume,
    pad_voxels: int = 3,
    companion_mask: np.ndarray | None = None,
) -> tuple[np.ndarray, Volume, np.ndarray | None]:
    """Crop ``mask`` and ``volume`` to the mask's own bounding box (plus a
    small pad), discarding empty space around the segmented region.

    This is meant to *replace* the caller's references to the original
    ``mask``/``volume``, not sit alongside them — the point is to let the
    (potentially much larger) original arrays be garbage collected before
    mesh generation, not just to hand meshing a smaller view while the
    full-size arrays stay referenced elsewhere. For an ROI prior far larger
    than the organ itself (e.g. a full sample-holder tube's bounding box
    for a much smaller specimen), that's the difference between fitting in
    memory and an OOM kill on large real volumes, not just a speed tweak.
    The cropped region still contains 100% of the mask, so the resulting
    mesh is identical either way.

    Always returns a 3-tuple ``(mask, volume, companion_mask)`` —
    ``companion_mask`` is ``None`` through unchanged when not supplied,
    e.g. a caller-supplied ground-truth mask for validation, cropped with
    the exact same bounding box so it stays shape-compatible with the result.
    """
    if not mask.any():
        return mask, volume, companion_mask

    nz, ny, nx = mask.shape
    zz, yy, xx = np.nonzero(mask)
    z0, z1 = max(0, zz.min() - pad_voxels), min(nz, zz.max() + pad_voxels + 1)
    y0, y1 = max(0, yy.min() - pad_voxels), min(ny, yy.max() + pad_voxels + 1)
    x0, x1 = max(0, xx.min() - pad_voxels), min(nx, xx.max() + pad_voxels + 1)

    cropped_mask = mask[z0:z1, y0:y1, x0:x1].copy()
    cropped_array = volume.array[z0:z1, y0:y1, x0:x1].copy()
    new_origin = volume.index_to_world(np.array([[x0, y0, z0]], dtype=np.float64))[0]

    cropped_volume = Volume(
        array=cropped_array,
        spacing=volume.spacing,
        origin=tuple(new_origin),
        direction=volume.direction,
        modality=volume.modality,
        source_path=volume.source_path,
    )

    cropped_companion = None if companion_mask is None else companion_mask[z0:z1, y0:y1, x0:x1].copy()
    return cropped_mask, cropped_volume, cropped_companion
