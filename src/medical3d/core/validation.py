"""Validation: the one pipeline stage every organ pipeline must run before
declaring a result usable.

Three independent checks are combined:

  1. **Mesh quality** — is the reconstructed surface watertight and
     consistently wound? A non-watertight mesh has an ill-defined volume
     and will not 3D print or export cleanly.
  2. **Anatomical plausibility** — does the reconstructed volume fall in a
     literature-informed physiological range for the organ? This is a
     coarse sanity check, not ground truth — it catches gross segmentation
     failures (e.g. leaking into a neighboring structure, or capturing only
     a fragment) even when no expert-labeled mask is available.
  3. **Overlap against ground truth** (optional) — Dice/Jaccard/mean surface
     distance against an expert-labeled mask, when one is supplied. This is
     how the Dice scores referenced in project history (liver 0.918, lung
     0.862) were originally measured, and how any future regression testing
     against labeled data should be done.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.spatial import cKDTree

from medical3d.core.mesh_ops import MeshQualityReport

# Adult reference volume ranges in mL, from cross-sectional CT/MRI organ
# volumetry literature. These are intentionally wide (they span normal
# physiological variation, not just measurement error) — the point is to
# flag gross failures, not to grade accuracy.
PLAUSIBLE_VOLUME_RANGES_ML: dict[str, tuple[float, float]] = {
    "lungs": (2000.0, 7000.0),
    "heart": (300.0, 900.0),
    "liver": (1000.0, 2500.0),
    "kidneys": (200.0, 450.0),
    "brain": (1000.0, 1600.0),
}


@dataclass(frozen=True)
class OverlapMetrics:
    dice: float
    jaccard: float
    mean_surface_distance_mm: float
    hausdorff_distance_mm: float


@dataclass(frozen=True)
class ValidationReport:
    organ: str
    volume_ml: float
    is_plausible_volume: bool
    plausible_range_ml: tuple[float, float]
    mesh_quality: MeshQualityReport
    overlap: OverlapMetrics | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """A minimal, conservative pass/fail gate: watertight mesh and a
        plausible volume. Overlap metrics (when available) are reported but
        not part of the gate, since they require ground truth most users
        will not have.
        """
        return self.mesh_quality.is_watertight and self.is_plausible_volume

    def as_dict(self) -> dict:
        return {
            "organ": self.organ,
            "volume_ml": self.volume_ml,
            "is_plausible_volume": self.is_plausible_volume,
            "plausible_range_ml": self.plausible_range_ml,
            "passed": self.passed,
            "mesh_quality": {
                "is_watertight": self.mesh_quality.is_watertight,
                "is_winding_consistent": self.mesh_quality.is_winding_consistent,
                "euler_number": self.mesh_quality.euler_number,
                "num_bodies": self.mesh_quality.num_bodies,
            },
            "overlap": None
            if self.overlap is None
            else {
                "dice": self.overlap.dice,
                "jaccard": self.overlap.jaccard,
                "mean_surface_distance_mm": self.overlap.mean_surface_distance_mm,
                "hausdorff_distance_mm": self.overlap.hausdorff_distance_mm,
            },
            "warnings": self.warnings,
        }


def dice_coefficient(prediction: np.ndarray, ground_truth: np.ndarray) -> float:
    pred = prediction.astype(bool)
    gt = ground_truth.astype(bool)
    intersection = np.logical_and(pred, gt).sum()
    denom = pred.sum() + gt.sum()
    if denom == 0:
        return 1.0 if intersection == 0 else 0.0
    return float(2.0 * intersection / denom)


def jaccard_index(prediction: np.ndarray, ground_truth: np.ndarray) -> float:
    pred = prediction.astype(bool)
    gt = ground_truth.astype(bool)
    intersection = np.logical_and(pred, gt).sum()
    union = np.logical_or(pred, gt).sum()
    if union == 0:
        return 1.0 if intersection == 0 else 0.0
    return float(intersection / union)


def surface_distance_metrics(
    prediction: np.ndarray, ground_truth: np.ndarray, spacing: tuple[float, float, float]
) -> tuple[float, float]:
    """Mean and Hausdorff (max) symmetric surface distance in millimeters,
    computed between the boundary voxels of two masks.
    """
    pred_surface = _surface_points_mm(prediction, spacing)
    gt_surface = _surface_points_mm(ground_truth, spacing)
    if len(pred_surface) == 0 or len(gt_surface) == 0:
        return float("nan"), float("nan")

    tree_gt = cKDTree(gt_surface)
    tree_pred = cKDTree(pred_surface)
    d_pred_to_gt, _ = tree_gt.query(pred_surface)
    d_gt_to_pred, _ = tree_pred.query(gt_surface)

    all_dists = np.concatenate([d_pred_to_gt, d_gt_to_pred])
    mean_distance = float(all_dists.mean())
    hausdorff = float(max(d_pred_to_gt.max(), d_gt_to_pred.max()))
    return mean_distance, hausdorff


def _surface_points_mm(mask: np.ndarray, spacing: tuple[float, float, float]) -> np.ndarray:
    from scipy import ndimage

    mask = mask.astype(bool)
    if not mask.any():
        return np.empty((0, 3))
    eroded = ndimage.binary_erosion(mask)
    boundary = mask & ~eroded
    zyx = np.argwhere(boundary)
    sx, sy, sz = spacing
    xyz_mm = zyx[:, ::-1] * np.array([sx, sy, sz])
    return xyz_mm


def compute_overlap_metrics(
    prediction: np.ndarray, ground_truth: np.ndarray, spacing: tuple[float, float, float]
) -> OverlapMetrics:
    mean_dist, hausdorff = surface_distance_metrics(prediction, ground_truth, spacing)
    return OverlapMetrics(
        dice=dice_coefficient(prediction, ground_truth),
        jaccard=jaccard_index(prediction, ground_truth),
        mean_surface_distance_mm=mean_dist,
        hausdorff_distance_mm=hausdorff,
    )


def validate_segmentation(
    organ: str,
    volume_ml: float,
    mesh_quality: MeshQualityReport,
    prediction_mask: np.ndarray | None = None,
    ground_truth_mask: np.ndarray | None = None,
    spacing: tuple[float, float, float] | None = None,
) -> ValidationReport:
    warnings: list[str] = []

    plausible_range = PLAUSIBLE_VOLUME_RANGES_ML.get(organ.lower())
    if plausible_range is None:
        warnings.append(f"No plausibility range configured for organ '{organ}'")
        is_plausible = True
    else:
        low, high = plausible_range
        is_plausible = low <= volume_ml <= high
        if not is_plausible:
            warnings.append(
                f"Reconstructed volume {volume_ml:.1f} mL is outside the "
                f"plausible adult range [{low}, {high}] mL for {organ}"
            )
        plausible_range = (low, high)

    if not mesh_quality.is_watertight:
        warnings.append("Mesh is not watertight — volume/export may be unreliable")
    if mesh_quality.num_bodies > 3:
        warnings.append(
            f"Mesh has {mesh_quality.num_bodies} disconnected components — "
            "check for segmentation fragmentation or noise islands"
        )

    overlap = None
    if prediction_mask is not None and ground_truth_mask is not None and spacing is not None:
        overlap = compute_overlap_metrics(prediction_mask, ground_truth_mask, spacing)

    return ValidationReport(
        organ=organ,
        volume_ml=volume_ml,
        is_plausible_volume=is_plausible,
        plausible_range_ml=plausible_range or (float("nan"), float("nan")),
        mesh_quality=mesh_quality,
        overlap=overlap,
        warnings=warnings,
    )
