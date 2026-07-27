"""Lung preprocessing: denoise, then (optionally) resample to isotropic spacing.

No ROI cropping is needed here — unlike liver/heart/kidneys, lung tissue is
separable from everything else by intensity alone, so preprocessing only
needs to condition the signal, not restrict the search region.
"""

from __future__ import annotations

from medical3d.core.config import OrganConfig
from medical3d.core.preprocessing_utils import gaussian_denoise, resample_to_isotropic
from medical3d.core.volume import Volume


def preprocess(volume: Volume, config: OrganConfig) -> Volume:
    denoised = gaussian_denoise(volume, sigma_mm=config.get("denoise_sigma_mm", 0.8))

    if config.get("resample_isotropic", True):
        denoised = resample_to_isotropic(
            denoised, target_spacing_mm=config.get("isotropic_spacing_mm")
        )

    return denoised
