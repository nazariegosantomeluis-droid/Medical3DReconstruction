"""Brain segmentation — ex-vivo synchrotron tomography.

A "complete-organ" scan has brain tissue filling nearly the whole
sample-holder tube (see preprocessing.py), so once the tube is excluded
geometrically, a low intensity threshold (well above the near-zero
gaps/artifacts, well below actual tissue) plus largest-connected-component
is enough — there is no separate mounting medium population to exclude by
intensity the way heart/liver/kidney specimens need.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage

from medical3d.core.config import OrganConfig
from medical3d.core.preprocessing_utils import largest_connected_components
from medical3d.core.volume import Volume


def segment(volume: Volume, config: OrganConfig) -> np.ndarray:
    threshold = config.get("tissue_intensity_threshold", 2000)
    tissue = volume.array > threshold

    opened = ndimage.binary_opening(tissue, structure=np.ones((3, 3, 3)))

    return largest_connected_components(opened, n=1, min_voxels=1)
