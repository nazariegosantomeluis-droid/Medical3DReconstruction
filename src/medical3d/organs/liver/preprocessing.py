"""Liver preprocessing.

Two acquisition modalities, two preprocessing paths (see
``organs/heart/preprocessing.py`` for the same architectural point):

  * **CT** (clinical, in-vivo): crop to a right-upper-quadrant ROI, denoise,
    resample.
  * **synchrotron** (ex-vivo tomography, e.g. ESRF Human Organ Atlas): unlike
    the heart/brain specimens, the liver sample fills the frame with no
    empty sample-holder-tube margin visible in the slice images (checked
    against the real LADAF-2021-17 liver archive — corner and center voxel
    populations are the same order of magnitude, not the medium-vs-air
    contrast the tube crop in heart/brain relies on), so no geometric tube
    exclusion is needed — only intensity threshold and downsampling.
"""

from __future__ import annotations

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
        x_fraction=config.get("roi_x_fraction", [0.0, 0.65]),
        y_fraction=config.get("roi_y_fraction", [0.05, 0.65]),
        z_fraction=config.get("roi_z_fraction", [0.30, 0.75]),
    )
    iso = resample_to_isotropic(roi, target_spacing_mm=config.get("resample_isotropic_spacing_mm", 1.5))
    denoised = gaussian_denoise(iso, sigma_mm=config.get("denoise_sigma_mm", 1.0))
    return denoised


def _preprocess_synchrotron(volume: Volume, config: OrganConfig) -> Volume:
    """Optional additional downsampling — no tube crop (see module
    docstring). The liver archive is ~1.6 billion voxels at native
    resolution: too large to even *decode* at full resolution before any
    downsampling runs (that OOM-killed the process validating this
    pipeline), so the real reduction for this organ happens earlier, at
    load time (see ``load_stride`` in configs/liver_synchrotron.yaml and
    ``io.volume_loader.load_volume``). This step just supports an optional
    *additional* reduction on top of that, defaulting to a no-op (1).
    """
    downsample_factor = config.get("downsample_factor", 1)
    array = volume.array
    spacing = volume.spacing
    if downsample_factor > 1:
        array = array[::downsample_factor, ::downsample_factor, ::downsample_factor].copy()
        spacing = tuple(s * downsample_factor for s in spacing)
    return Volume(
        array=array,
        spacing=spacing,
        origin=volume.origin,
        direction=volume.direction,
        modality=volume.modality,
        source_path=volume.source_path,
    )
