import os

import SimpleITK as sitk


def load_volume(path: str):
    """
    Load a medical volume using SimpleITK.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Volume file not found: {path}")

    return sitk.ReadImage(path)
