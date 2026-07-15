import matplotlib.pyplot as plt
import SimpleITK as sitk


def show_middle_slice(image: sitk.Image):
    """
    Display the middle axial slice of a 3D medical image.
    """
    volume = sitk.GetArrayFromImage(image)

    if volume.ndim < 3:
        raise ValueError("Expected a 3D image volume")

    middle_slice = volume.shape[0] // 2

    plt.figure(figsize=(8, 8))
    plt.imshow(volume[middle_slice], cmap="gray")
    plt.title(f"Axial Slice {middle_slice}")
    plt.axis("off")
    plt.show()
