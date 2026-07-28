"""Brain segmentation — ex-vivo synchrotron tomography.

A "complete-organ" scan has brain tissue filling nearly the whole
sample-holder tube (see preprocessing.py), so once the tube is excluded
geometrically, there's no separate mounting-medium population to exclude
by intensity the way heart/liver/kidney specimens need — but the tissue
itself is bimodal: a histogram of the calibration slice shows a lower
population (~3700-4500 native units, mounting medium/fluid filling the
sulci between gyri) and a higher one (~5100-7900, actual parenchyma), with
a valley around 4900-5000. Thresholding below both (as an earlier version
of this config did, at 2000) merges them into a solid cylindrical mass
with no visible gyri/sulci; thresholding in the valley recovers a
recognizable folded cortical surface — see docs/ORGAN_PIPELINES.md.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage

from medical3d.core.config import OrganConfig
from medical3d.core.preprocessing_utils import largest_connected_components
from medical3d.core.volume import Volume


def segment(volume: Volume, config: OrganConfig) -> np.ndarray:
    threshold = config.get("tissue_intensity_threshold", 5000)
    tissue = volume.array > threshold

    opened = ndimage.binary_opening(tissue, structure=np.ones((3, 3, 3)))

    return largest_connected_components(opened, n=1, min_voxels=1)
