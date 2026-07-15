import SimpleITK as sitk


def print_volume_info(image: sitk.Image):
    """
    Print basic information about a medical volume.
    """

    print("\n========== VOLUME INFORMATION ==========\n")

    print(f"Dimensions      : {image.GetSize()}")

    print(f"Voxel Spacing   : {image.GetSpacing()}")

    print(f"Origin          : {image.GetOrigin()}")

    print(f"Direction       : {image.GetDirection()}")

    print(f"Pixel Type      : {image.GetPixelIDTypeAsString()}")