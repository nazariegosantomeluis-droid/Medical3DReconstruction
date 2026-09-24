"""Kidney preprocessing.

Two acquisition modalities, two preprocessing paths (see
``organs/heart/preprocessing.py`` for the same architectural point):

  * **CT** (clinical, in-vivo): crop to a bilateral posterior-abdomen ROI,
    denoise, resample.
  * **synchrotron** (ex-vivo tomography): the K292 specimen archive used
    here is a *single* kidney (not a bilateral CT abdomen scan), and like
    the liver archive it fills the frame with no tube margin visible, so
    only downsampling is needed — no ROI crop, no tube exclusion.
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
        x_fraction=config.get("roi_x_fraction", [0.10, 0.90]),
        y_fraction=config.get("roi_y_fraction", [0.45, 0.90]),
        z_fraction=config.get("roi_z_fraction", [0.35, 0.65]),
    )
    iso = resample_to_isotropic(roi, target_spacing_mm=config.get("resample_isotropic_spacing_mm", 1.2))
    denoised = gaussian_denoise(iso, sigma_mm=config.get("denoise_sigma_mm", 1.0))
    return denoised


def _preprocess_synchrotron(volume: Volume, config: OrganConfig) -> Volume:
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
