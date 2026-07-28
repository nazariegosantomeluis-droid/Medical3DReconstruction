"""Volume loading and validation."""

from __future__ import annotations

import os
import zipfile

import numpy as np
import pytest
import SimpleITK as sitk

from medical3d.io import VolumeLoadError, load_volume


def test_load_volume_missing_path_raises(tmp_path):
    with pytest.raises(VolumeLoadError):
        load_volume(str(tmp_path / "does_not_exist.nrrd"))


def test_load_volume_rejects_bad_modality(tmp_path):
    fake = tmp_path / "x.nrrd"
    fake.write_bytes(b"not a real nrrd")
    with pytest.raises(VolumeLoadError):
        load_volume(str(fake), modality="XRAY")


def test_load_volume_rejects_unsupported_extension(tmp_path):
    fake = tmp_path / "volume.txt"
    fake.write_text("nope")
    with pytest.raises(VolumeLoadError):
        load_volume(str(fake))


def test_load_volume_roundtrip_nrrd(tmp_path):
    array = np.random.default_rng(0).integers(-1000, 1000, size=(10, 12, 14)).astype(np.int16)
    image = sitk.GetImageFromArray(array)
    image.SetSpacing((1.0, 1.0, 2.0))
    image.SetOrigin((5.0, -3.0, 10.0))
    path = str(tmp_path / "volume.nrrd")
    sitk.WriteImage(image, path)

    volume = load_volume(path, modality="CT")
    assert volume.array.shape == array.shape
    assert volume.spacing == (1.0, 1.0, 2.0)
    assert volume.origin == (5.0, -3.0, 10.0)
    assert volume.modality == "CT"


def test_load_real_ct_fixture(real_ct_path):
    volume = load_volume(real_ct_path, modality="CT")
    assert volume.array.ndim == 3
    assert all(s > 0 for s in volume.spacing)
    assert volume.array.min() < -500  # contains air/lung-range HU


def _write_slice_png_stack(directory: str, num_slices: int = 6, size: int = 24) -> None:
    rng = np.random.default_rng(0)
    for z in range(num_slices):
        slice_arr = rng.integers(20000, 26000, size=(size, size)).astype(np.uint16)
        image = sitk.GetImageFromArray(slice_arr)
        sitk.WriteImage(image, os.path.join(directory, f"slice_{z:04d}.png"))


def test_load_volume_synchrotron_requires_spacing(tmp_path):
    _write_slice_png_stack(str(tmp_path))
    with pytest.raises(VolumeLoadError):
        load_volume(str(tmp_path), modality="synchrotron")


def test_load_volume_synchrotron_from_directory(tmp_path):
    _write_slice_png_stack(str(tmp_path), num_slices=6, size=24)
    volume = load_volume(str(tmp_path), modality="synchrotron", spacing_mm=(0.2, 0.2, 0.3))
    assert volume.array.shape == (6, 24, 24)
    assert volume.spacing == (0.2, 0.2, 0.3)
    assert volume.modality == "synchrotron"


def test_load_volume_synchrotron_from_zip(tmp_path):
    slices_dir = tmp_path / "slices"
    slices_dir.mkdir()
    _write_slice_png_stack(str(slices_dir), num_slices=5, size=20)

    zip_path = tmp_path / "slices.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        for name in sorted(os.listdir(slices_dir)):
            archive.write(slices_dir / name, arcname=name)

    volume = load_volume(str(zip_path), modality="synchrotron", spacing_mm=(0.17, 0.17, 0.17))
    assert volume.array.shape == (5, 20, 20)
    assert volume.spacing == (0.17, 0.17, 0.17)


def test_load_volume_synchrotron_rejects_empty_zip(tmp_path):
    zip_path = tmp_path / "empty.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("readme.txt", "no images here")
    with pytest.raises(VolumeLoadError):
        load_volume(str(zip_path), modality="synchrotron", spacing_mm=(0.1, 0.1, 0.1))
