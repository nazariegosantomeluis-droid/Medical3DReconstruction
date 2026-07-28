"""Abstract organ pipeline.

Every organ implements its own ``preprocess`` / ``segment`` / ``postprocess``
— there is no shared segmentation algorithm, because lungs (air-separated),
liver (homogeneous soft tissue, needs a spatial prior), and heart/kidneys
(boundary-aware, similar density to neighbors) each fail under a
one-size-fits-all thresholding approach. What *is* shared is generic
geometry processing (marching cubes, mesh smoothing/decimation, metrics,
validation plumbing) — that's standard library code, not segmentation logic,
and duplicating it per organ would be pure copy-paste with no scientific
benefit.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import trimesh

from medical3d.core.config import OrganConfig
from medical3d.core.mesh import MeshMetrics, compute_mesh_metrics, mask_to_mesh
from medical3d.core.mesh_ops import assess_mesh_quality, decimate_mesh, repair_mesh, smooth_mesh
from medical3d.core.preprocessing_utils import crop_to_mask_bbox
from medical3d.core.validation import ValidationReport, validate_segmentation
from medical3d.core.volume import Volume


@dataclass(frozen=True)
class PipelineResult:
    organ: str
    volume: Volume
    mask: np.ndarray
    mesh: trimesh.Trimesh
    metrics: MeshMetrics
    validation: ValidationReport


class OrganPipeline(ABC):
    """Base class every organ-specific pipeline extends."""

    organ_name: str = ""

    def __init__(self, config: OrganConfig):
        if config.organ.lower() != self.organ_name.lower():
            raise ValueError(
                f"Config organ '{config.organ}' does not match pipeline "
                f"'{self.organ_name}'"
            )
        self.config = config

    @abstractmethod
    def preprocess(self, volume: Volume) -> Volume:
        """Organ-specific denoising, windowing, and/or resampling."""

    @abstractmethod
    def segment(self, volume: Volume) -> np.ndarray:
        """Organ-specific segmentation. Returns a binary mask, same shape as volume.array."""

    @abstractmethod
    def postprocess(self, mask: np.ndarray, volume: Volume) -> np.ndarray:
        """Organ-specific mask cleanup (component selection, hole filling, morphology)."""

    def generate_mesh(self, mask: np.ndarray, volume: Volume) -> trimesh.Trimesh:
        return mask_to_mesh(mask, volume, smoothing_sigma=self.config.mesh_smoothing_sigma)

    def optimize_mesh(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        # Decimate before smoothing, not after: Taubin smoothing's cost
        # scales with face count, and a raw marching-cubes mesh can be
        # orders of magnitude larger than the final target (millions of
        # faces for a high-resolution volume) — smoothing that first would
        # mean paying for detail that's about to be thrown away anyway.
        mesh = decimate_mesh(mesh, target_face_fraction=self.config.mesh_decimate_target_fraction)
        mesh = smooth_mesh(mesh, iterations=self.config.mesh_taubin_iterations)
        mesh = repair_mesh(mesh)
        return mesh

    def validate(
        self,
        mask: np.ndarray,
        mesh: trimesh.Trimesh,
        volume: Volume,
        metrics: MeshMetrics,
        ground_truth_mask: np.ndarray | None = None,
    ) -> ValidationReport:
        quality = assess_mesh_quality(mesh)
        return validate_segmentation(
            organ=self.organ_name,
            volume_ml=metrics.volume_ml,
            mesh_quality=quality,
            prediction_mask=mask,
            ground_truth_mask=ground_truth_mask,
            spacing=volume.spacing,
        )

    def run(self, volume: Volume, ground_truth_mask: np.ndarray | None = None) -> PipelineResult:
        """Run the full pipeline: preprocess -> segment -> postprocess -> mesh -> optimize -> validate."""
        preprocessed = self.preprocess(volume)

        raw_mask = self.segment(preprocessed)
        mask = self.postprocess(raw_mask, preprocessed)
        del raw_mask

        # Crop to the segmented region's own bounding box and *replace*
        # mask/preprocessed with the cropped versions, rather than keeping
        # both around — for a preprocessing ROI far larger than the organ
        # itself (e.g. a sample-holder tube's full bounding box for a much
        # smaller specimen), the difference is not just wasted compute in
        # mesh generation, it's whether the whole pipeline fits in memory
        # on a large real volume. ground_truth_mask, if supplied, is
        # cropped identically so it stays shape-compatible.
        mask, preprocessed, ground_truth_mask = crop_to_mask_bbox(
            mask, preprocessed, companion_mask=ground_truth_mask
        )

        mesh = self.generate_mesh(mask, preprocessed)
        mesh = self.optimize_mesh(mesh)

        metrics = compute_mesh_metrics(mesh)
        validation = self.validate(mask, mesh, preprocessed, metrics, ground_truth_mask)

        return PipelineResult(
            organ=self.organ_name,
            volume=preprocessed,
            mask=mask,
            mesh=mesh,
            metrics=metrics,
            validation=validation,
        )
