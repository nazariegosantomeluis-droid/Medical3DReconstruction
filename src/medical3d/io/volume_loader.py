"""Loading CT/MRI/ex-vivo tomography volumes from disk.

Supports three input shapes:
  * A single volume file (``.nrrd``, ``.nii``, ``.nii.gz``, ``.mha``, ``.mhd``).
  * A directory containing a single DICOM series.
  * ``modality="synchrotron"``: a directory or ``.zip`` of 2D slice images
    (``.jp2``/``.j2k``/``.tif``/``.tiff``/``.png``), the distribution format
    used by ex-vivo synchrotron tomography archives (e.g. the ESRF Human
    Organ Atlas / HiP-CT). These carry no reliable physical-spacing metadata
    in the image files themselves, so ``spacing_mm`` must be supplied
    explicitly — there is no DICOM header to trust here.

Both paths are validated before being handed to the rest of the pipeline:
we refuse empty/degenerate volumes, non-3D images, and non-finite spacing,
because a garbage volume silently propagates into a garbage mesh several
stages later where it is much harder to diagnose.
"""

from __future__ import annotations

import math
import os
import tempfile
import zipfile

import numpy as np
import SimpleITK as sitk

from medical3d.core.volume import Volume

_SINGLE_FILE_EXTENSIONS = (".nrrd", ".nhdr", ".nii", ".nii.gz", ".mha", ".mhd")
_SLICE_IMAGE_EXTENSIONS = (".jp2", ".j2k", ".tif", ".tiff", ".png")
_MODALITIES = ("CT", "MRI", "synchrotron")


class VolumeLoadError(RuntimeError):
    """Raised when a volume cannot be loaded or fails validation."""


def load_volume(
    path: str,
    modality: str = "CT",
    spacing_mm: tuple[float, float, float] | None = None,
    load_stride: int = 1,
) -> Volume:
    """Load a volume from a file, a DICOM series directory, or (with
    ``modality="synchrotron"``) a directory/zip of 2D slice images.

    Args:
        path: Path to a volume file, a directory holding one DICOM series,
            or (for ``modality="synchrotron"``) a directory or ``.zip`` of
            2D slice images.
        modality: ``"CT"``, ``"MRI"``, or ``"synchrotron"``. CT pipelines
            assume Hounsfield units; this is not auto-detected because
            DICOM tags are not reliable enough to gate segmentation logic
            on. ``"synchrotron"`` is for ex-vivo phase-contrast tomography
            (arbitrary 16-bit intensity scale, no HU semantics).
        spacing_mm: Required when ``modality="synchrotron"`` — the
            (x, y, z) voxel spacing in millimeters, since slice-image
            archives don't carry it. Ignored for CT/MRI (spacing comes
            from the file/DICOM header).
        load_stride: Only used with ``modality="synchrotron"``. Skips every
            ``load_stride``-th slice/pixel *while decoding*, before the
            full-resolution array is ever materialized. Some archives
            (e.g. a ~1.6 billion voxel liver overview scan) are too large
            to decode at native resolution and then downsample afterward —
            decoding alone can exceed a typical machine's RAM before the
            pipeline's own preprocessing downsample step ever runs.
            Physical spacing is scaled by this factor accordingly. Default
            1 (no striding) preserves the existing behavior.

    Raises:
        VolumeLoadError: if the path does not exist, no readable volume is
            found, or the loaded image fails basic sanity checks.
    """
    if modality not in _MODALITIES:
        raise VolumeLoadError(f"Unsupported modality '{modality}', expected one of {_MODALITIES}")

    if not os.path.exists(path):
        raise VolumeLoadError(f"Path not found: {path}")

    if modality == "synchrotron":
        if spacing_mm is None or len(spacing_mm) != 3:
            raise VolumeLoadError(
                "modality='synchrotron' requires an explicit spacing_mm=(sx, sy, sz) — "
                "slice-image archives (JP2/TIFF/PNG stacks) carry no reliable physical "
                "spacing metadata to read it from."
            )
        image = _load_slice_sequence(path, spacing_mm, load_stride)
    elif os.path.isdir(path):
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


def _load_slice_sequence(path: str, spacing_mm: tuple[float, float, float], load_stride: int = 1) -> sitk.Image:
    if path.lower().endswith(".zip"):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with zipfile.ZipFile(path) as archive:
                members = [n for n in archive.namelist() if n.lower().endswith(_SLICE_IMAGE_EXTENSIONS)]
                if not members:
                    raise VolumeLoadError(
                        f"No slice images ({_SLICE_IMAGE_EXTENSIONS}) found in zip '{path}'"
                    )
                archive.extractall(tmp_dir, members=members)
            image = _read_slice_directory(tmp_dir, load_stride)
    elif os.path.isdir(path):
        image = _read_slice_directory(path, load_stride)
    else:
        raise VolumeLoadError(
            f"modality='synchrotron' expects a directory or .zip of 2D slice images, got '{path}'"
        )
    scaled_spacing = tuple(float(s) * load_stride for s in spacing_mm)
    image.SetSpacing(scaled_spacing)
    return image


def _read_slice_directory(directory: str, load_stride: int = 1) -> sitk.Image:
    files = []
    for root, _dirs, names in os.walk(directory):
        for name in names:
            if name.lower().endswith(_SLICE_IMAGE_EXTENSIONS):
                files.append(os.path.join(root, name))
    files.sort()
    files = files[::load_stride]

    if len(files) < 2:
        raise VolumeLoadError(f"Found only {len(files)} slice image(s) under '{directory}'; need at least 2.")

    try:
        first_slice = sitk.GetArrayFromImage(sitk.ReadImage(files[0]))[::load_stride, ::load_stride]
    except RuntimeError as exc:
        raise VolumeLoadError(f"Failed to read slice image '{files[0]}': {exc}") from exc
    if first_slice.ndim != 2:
        raise VolumeLoadError(f"Expected 2D slice images, got {first_slice.ndim}D from '{files[0]}'")

    array = np.empty((len(files), *first_slice.shape), dtype=np.float32)
    array[0] = first_slice
    for i, file_path in enumerate(files[1:], start=1):
        try:
            array[i] = sitk.GetArrayFromImage(sitk.ReadImage(file_path))[::load_stride, ::load_stride]
        except RuntimeError as exc:
            raise VolumeLoadError(f"Failed to read slice image '{file_path}': {exc}") from exc

    return sitk.GetImageFromArray(array)


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
