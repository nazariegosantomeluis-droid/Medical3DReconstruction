"""Kidney preprocessing: crop to the bilateral posterior-abdomen ROI, denoise, resample."""

from __future__ import annotations

from medical3d.core.config import OrganConfig
from medical3d.core.preprocessing_utils import crop_fractional_roi, gaussian_denoise, resample_to_isotropic
from medical3d.core.volume import Volume


def preprocess(volume: Volume, config: OrganConfig) -> Volume:
    roi = crop_fractional_roi(
        volume,
        x_fraction=config.get("roi_x_fraction", [0.10, 0.90]),
        y_fraction=config.get("roi_y_fraction", [0.45, 0.90]),
        z_fraction=config.get("roi_z_fraction", [0.35, 0.65]),
    )
    iso = resample_to_isotropic(roi, target_spacing_mm=config.get("resample_isotropic_spacing_mm", 1.2))
    denoised = gaussian_denoise(iso, sigma_mm=config.get("denoise_sigma_mm", 1.0))
    return denoised
