from __future__ import annotations

import numpy as np

from medical3d.core.volume import Volume
from medical3d.organs.base import OrganPipeline
from medical3d.organs.brain.postprocessing import postprocess as _postprocess
from medical3d.organs.brain.preprocessing import preprocess as _preprocess
from medical3d.organs.brain.segmentation import segment as _segment


class BrainPipeline(OrganPipeline):
    organ_name = "brain"

    def preprocess(self, volume: Volume) -> Volume:
        return _preprocess(volume, self.config)

    def segment(self, volume: Volume) -> np.ndarray:
        return _segment(volume, self.config)

    def postprocess(self, mask: np.ndarray, volume: Volume) -> np.ndarray:
        return _postprocess(mask, volume, self.config)
