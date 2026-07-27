"""Heart preprocessing: crop to the mediastinal ROI, then denoise and resample.

The ROI crop is the heart-specific anatomical prior (no atlas registration
is used anywhere in this project) — everything after it is generic image
conditioning shared through ``core.preprocessing_utils``.
"""

from __future__ import annotations

from medical3d.core.config import OrganConfig
from medical3d.core.preprocessing_utils import crop_fractional_roi, gaussian_denoise, resample_to_isotropic
from medical3d.core.volume import Volume


def preprocess(volume: Volume, config: OrganConfig) -> Volume:
    roi = crop_fractional_roi(
        volume,
        x_fraction=config.get("roi_x_fraction", [0.25, 0.75]),
        y_fraction=config.get("roi_y_fraction", [0.15, 0.75]),
        z_fraction=config.get("roi_z_fraction", [0.15, 0.85]),
    )
    iso = resample_to_isotropic(roi, target_spacing_mm=config.get("resample_isotropic_spacing_mm", 1.2))
    denoised = gaussian_denoise(iso, sigma_mm=config.get("denoise_sigma_mm", 1.0))
    return denoised
