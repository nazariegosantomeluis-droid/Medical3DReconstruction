from __future__ import annotations

import numpy as np

from medical3d.core.volume import Volume
from medical3d.organs.base import OrganPipeline
from medical3d.organs.lungs.postprocessing import postprocess as _postprocess
from medical3d.organs.lungs.preprocessing import preprocess as _preprocess
from medical3d.organs.lungs.segmentation import segment as _segment


class LungsPipeline(OrganPipeline):
    organ_name = "lungs"

    def preprocess(self, volume: Volume) -> Volume:
        return _preprocess(volume, self.config)

    def segment(self, volume: Volume) -> np.ndarray:
        return _segment(volume, self.config)

    def postprocess(self, mask: np.ndarray, volume: Volume) -> np.ndarray:
        return _postprocess(mask, volume, self.config)
