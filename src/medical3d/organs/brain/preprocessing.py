"""Brain preprocessing — ex-vivo synchrotron tomography only.

Unlike heart/liver/kidney specimens (a smaller organ surrounded by a
visible gap of mounting medium inside the sample-holder tube), a
"complete-organ" brain scan has the specimen filling almost the entire
tube — there is no separate low-density medium to threshold away. The
only geometric prior needed is excluding the tube itself, exactly as in
``organs/heart/preprocessing.py``; what's inside the tube is (almost)
entirely brain tissue.

There is no clinical CT/MRI branch here: this project has no clinical
brain data to validate a boundary-aware pipeline against (skull-stripping
plus parenchyma segmentation from clinical imaging is its own, well-studied
problem — building one blind, with nothing to check it against, would not
meet this project's own bar for validated pipelines). See
docs/ORGAN_PIPELINES.md.
"""

from __future__ import annotations

import numpy as np

from medical3d.core.config import OrganConfig
from medical3d.core.volume import Volume


def preprocess(volume: Volume, config: OrganConfig) -> Volume:
    if volume.modality != "synchrotron":
        raise ValueError(
            f"Brain pipeline only supports modality='synchrotron' (ex-vivo tomography); "
            f"got '{volume.modality}'. There is no clinical CT/MRI brain pipeline in this project."
        )

    radius_fraction = config.get("tube_radius_fraction", 0.485)
    downsample_factor = config.get("downsample_factor", 2)

    nz, ny, nx = volume.array.shape
    cy, cx = (ny - 1) / 2.0, (nx - 1) / 2.0
    radius_px = radius_fraction * min(ny, nx)
    yy, xx = np.meshgrid(np.arange(ny), np.arange(nx), indexing="ij")
    inside_tube = (yy - cy) ** 2 + (xx - cx) ** 2 <= radius_px**2

    ys, xs = np.nonzero(inside_tube)
    pad = 5
    y0, y1 = max(0, ys.min() - pad), min(ny, ys.max() + pad + 1)
    x0, x1 = max(0, xs.min() - pad), min(nx, xs.max() + pad + 1)

    cropped = volume.array[:, y0:y1, x0:x1].copy()
    cropped[:, ~inside_tube[y0:y1, x0:x1]] = 0.0

    spacing = volume.spacing
    if downsample_factor > 1:
        cropped = cropped[::downsample_factor, ::downsample_factor, ::downsample_factor].copy()
        spacing = tuple(s * downsample_factor for s in spacing)

    new_origin = volume.index_to_world(np.array([[x0, y0, 0]], dtype=np.float64))[0]
    return Volume(
        array=cropped,
        spacing=spacing,
        origin=tuple(new_origin),
        direction=volume.direction,
        modality=volume.modality,
        source_path=volume.source_path,
    )
