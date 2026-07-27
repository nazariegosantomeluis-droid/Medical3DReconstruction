"""Loading CT/MRI volumes from disk.

Supports two input shapes:
  * A single volume file (``.nrrd``, ``.nii``, ``.nii.gz``, ``.mha``, ``.mhd``).
  * A directory containing a single DICOM series.

Both paths are validated before being handed to the rest of the pipeline:
we refuse empty/degenerate volumes, non-3D images, and non-finite spacing,
because a garbage volume silently propagates into a garbage mesh several
stages later where it is much harder to diagnose.
"""

from __future__ import annotations

import math
import os

import SimpleITK as sitk

from medical3d.core.volume import Volume

_SINGLE_FILE_EXTENSIONS = (".nrrd", ".nhdr", ".nii", ".nii.gz", ".mha", ".mhd")


class VolumeLoadError(RuntimeError):
    """Raised when a volume cannot be loaded or fails validation."""


def load_volume(path: str, modality: str = "CT") -> Volume:
    """Load a CT/MRI volume from a file or a DICOM series directory.

    Args:
        path: Path to a volume file, or a directory holding one DICOM series.
        modality: ``"CT"`` or ``"MRI"``. CT pipelines assume Hounsfield
            units; this is not auto-detected because DICOM tags are not
            reliable enough to gate segmentation logic on.

    Raises:
        VolumeLoadError: if the path does not exist, no readable volume is
            found, or the loaded image fails basic sanity checks.
    """
    if modality not in ("CT", "MRI"):
        raise VolumeLoadError(f"Unsupported modality '{modality}', expected 'CT' or 'MRI'")

    if not os.path.exists(path):
        raise VolumeLoadError(f"Path not found: {path}")

    if os.path.isdir(path):
        image = _load_dicom_series(path)
    else:
        image = _load_single_file(path)

    _validate_image(image, path)
    return Volume.from_sitk_image(image, modality=modality, source_path=path)


def _load_single_file(path: str) -> sitk.Image:
    lower = path.lower()
    if not lower.endswith(_SINGLE_FILE_EXTENSIONS):
        raise VolumeLoadError(
            f"Unsupported file extension for '{path}'. "
            f"Expected one of {_SINGLE_FILE_EXTENSIONS} or a DICOM series directory."
        )
    try:
        image = sitk.ReadImage(path)
    except RuntimeError as exc:
        raise VolumeLoadError(f"Failed to read volume '{path}': {exc}") from exc
    return sitk.Cast(image, sitk.sitkFloat32)


def _load_dicom_series(directory: str) -> sitk.Image:
    reader = sitk.ImageSeriesReader()
    series_ids = reader.GetGDCMSeriesIDs(directory)
    if not series_ids:
        raise VolumeLoadError(f"No DICOM series found in directory: {directory}")
    if len(series_ids) > 1:
        raise VolumeLoadError(
            f"Directory '{directory}' contains {len(series_ids)} DICOM series; "
            "point to a directory with exactly one series."
        )
    file_names = reader.GetGDCMSeriesFileNames(directory, series_ids[0])
    if len(file_names) < 2:
        raise VolumeLoadError(
            f"DICOM series in '{directory}' has only {len(file_names)} slice(s); "
            "a 3D volume needs at least 2."
        )
    reader.SetFileNames(file_names)
    try:
        image = reader.Execute()
    except RuntimeError as exc:
        raise VolumeLoadError(f"Failed to read DICOM series in '{directory}': {exc}") from exc
    return sitk.Cast(image, sitk.sitkFloat32)


def _validate_image(image: sitk.Image, path: str) -> None:
    if image.GetDimension() != 3:
        raise VolumeLoadError(f"Expected a 3D volume, got {image.GetDimension()}D from '{path}'")

    size = image.GetSize()
    if any(dim < 2 for dim in size):
        raise VolumeLoadError(f"Degenerate volume dimensions {size} loaded from '{path}'")

    spacing = image.GetSpacing()
    if any((not math.isfinite(s)) or s <= 0 for s in spacing):
        raise VolumeLoadError(f"Invalid voxel spacing {spacing} loaded from '{path}'")

    origin = image.GetOrigin()
    if any(not math.isfinite(o) for o in origin):
        raise VolumeLoadError(f"Invalid origin {origin} loaded from '{path}'")
