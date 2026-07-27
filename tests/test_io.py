"""Volume loading and validation."""

from __future__ import annotations

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
