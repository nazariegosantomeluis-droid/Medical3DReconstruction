"""Lung segmentation: body-masked HU threshold + connected-component analysis.

Algorithm (classical, after Hu, Hoffman & Reinhardt 2001):
  1. Build a per-slice body silhouette: on each axial slice, take the
     largest connected region above ``body_threshold_hu`` (skin/chest wall)
     and fill it in, so lung-shaped low-HU regions *inside* the silhouette
     become part of the body mask. This is necessary, not cosmetic — the
     respiratory tract is one continuous air column from the airway opening
     down to the alveoli, so a plain 3D "remove whatever touches the volume
     border" pass leaks straight through the trachea and merges the lungs
     with the scanner's background air into a single component.
  2. Threshold at ``air_threshold_hu`` for an air-equivalent binary mask,
     restricted to inside the body silhouette from step 1. This keeps
     background air out regardless of how the airway connects to it.
  3. Keep the ``num_components`` largest remaining air pockets. The trachea
     and main bronchi form a much smaller connected volume than either
     lung, so simple size ranking (not explicit airway tracking) separates
     them.

This threshold is why lungs do not need boundary-aware segmentation the way
heart/kidney do: the HU separation from surrounding tissue is >500 HU, far
larger than any noise or partial-volume effect — once background air is
excluded, the remaining problem is purely geometric (pick the big blobs).
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage

from medical3d.core.config import OrganConfig
from medical3d.core.preprocessing_utils import largest_connected_components
from medical3d.core.volume import Volume


def segment(volume: Volume, config: OrganConfig) -> np.ndarray:
    body_threshold_hu = config.get("body_threshold_hu", -500)
    body_mask = _body_silhouette(volume.array, body_threshold_hu)

    air_threshold_hu = config.get("air_threshold_hu", -320)
    air_mask = (volume.array < air_threshold_hu) & body_mask

    num_components = config.get("num_components", 2)
    min_voxels = config.get("min_component_voxels", 1500)
    lungs_mask = largest_connected_components(air_mask, n=num_components, min_voxels=min_voxels)

    return lungs_mask


def _body_silhouette(array: np.ndarray, body_threshold_hu: float) -> np.ndarray:
    """Per-slice patient silhouette: largest above-threshold region, filled.

    Filling holes on each 2D slice (rather than in 3D) is what correctly
    turns the lung-shaped low-HU regions inside the chest wall into "body
    interior" without needing the lungs to already be segmented.
    """
    body = np.zeros_like(array, dtype=bool)
    for z in range(array.shape[0]):
        candidate = array[z] > body_threshold_hu
        if not candidate.any():
            continue
        labeled, num_features = ndimage.label(candidate)
        if num_features == 0:
            continue
        sizes = ndimage.sum(candidate, labeled, index=range(1, num_features + 1))
        largest_label = int(np.argmax(sizes)) + 1
        silhouette = labeled == largest_label
        body[z] = ndimage.binary_fill_holes(silhouette)
    return body
