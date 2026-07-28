"""Heart preprocessing.

Two acquisition modalities, two preprocessing paths — the anatomical prior
each needs is different, not just the parameters:

  * **CT** (clinical, in-vivo): crop to a mediastinal ROI (a coordinate-space
    heuristic standing in for atlas registration), then denoise and resample.
  * **synchrotron** (ex-vivo tomography, e.g. ESRF Human Organ Atlas): the
    specimen sits in a cylindrical sample-holder tube. The tube wall reads
    as very high intensity and the surrounding air/tube contributes nothing
    anatomical, so it's masked out geometrically (a circular crop per axial
    slice) rather than by an intensity threshold — the tube wall is denser
    than the tissue we want, so no single threshold could separate "tissue"
    from "tube" without also excluding it by position.
"""

from __future__ import annotations

import numpy as np

from medical3d.core.config import OrganConfig
from medical3d.core.preprocessing_utils import crop_fractional_roi, gaussian_denoise, resample_to_isotropic
from medical3d.core.volume import Volume


def preprocess(volume: Volume, config: OrganConfig) -> Volume:
    if volume.modality == "synchrotron":
        return _preprocess_synchrotron(volume, config)
    return _preprocess_ct(volume, config)


def _preprocess_ct(volume: Volume, config: OrganConfig) -> Volume:
    roi = crop_fractional_roi(
        volume,
        x_fraction=config.get("roi_x_fraction", [0.25, 0.75]),
        y_fraction=config.get("roi_y_fraction", [0.15, 0.75]),
        z_fraction=config.get("roi_z_fraction", [0.15, 0.85]),
    )
    iso = resample_to_isotropic(roi, target_spacing_mm=config.get("resample_isotropic_spacing_mm", 1.2))
    denoised = gaussian_denoise(iso, sigma_mm=config.get("denoise_sigma_mm", 1.0))
    return denoised


def _preprocess_synchrotron(volume: Volume, config: OrganConfig) -> Volume:
    """Exclude the sample-holder tube, crop to its bounding box, and
    (optionally) downsample.

    Only ever copies the *cropped* region, never the full raw array —
    these volumes are large enough (order of a billion voxels at native
    resolution) that an incidental full-array copy is the difference
    between comfortably fitting in memory and an OOM kill partway through
    the pipeline, not just wasted work.
    """
    radius_fraction = config.get("tube_radius_fraction", 0.465)
    downsample_factor = config.get("downsample_factor", 1)

    nz, ny, nx = volume.array.shape
    cy, cx = (ny - 1) / 2.0, (nx - 1) / 2.0
    radius_px = radius_fraction * min(ny, nx)
    yy, xx = np.meshgrid(np.arange(ny), np.arange(nx), indexing="ij")
    inside_tube = (yy - cy) ** 2 + (xx - cx) ** 2 <= radius_px**2

    ys, xs = np.nonzero(inside_tube)
    pad = 5
    y0, y1 = max(0, ys.min() - pad), min(ny, ys.max() + pad + 1)
    x0, x1 = max(0, xs.min() - pad), min(nx, xs.max() + pad + 1)

    cropped = volume.array[:, y0:y1, x0:x1].copy()
    # Zero out the sample-holder tube wall and everything outside it, on
    # every slice — this guarantees the intensity threshold in
    # segmentation.py never fires there, regardless of the tube wall's
    # (high) density.
    cropped[:, ~inside_tube[y0:y1, x0:x1]] = 0.0

    spacing = volume.spacing
    if downsample_factor > 1:
        cropped = cropped[::downsample_factor, ::downsample_factor, ::downsample_factor].copy()
        spacing = tuple(s * downsample_factor for s in spacing)

    new_origin = volume.index_to_world(np.array([[x0, y0, 0]], dtype=np.float64))[0]
    return Volume(
        array=cropped,
        spacing=spacing,
        origin=tuple(new_origin),
        direction=volume.direction,
        modality=volume.modality,
        source_path=volume.source_path,
    )
