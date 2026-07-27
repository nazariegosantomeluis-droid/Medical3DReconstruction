"""3D reconstruction visualization, plus a 2D slice viewer used only as a
secondary QA aid (checking segmentation against the source scan).

Rendering correctness notes (why these specific PyVista options are used):

  * ``mask_to_mesh`` already guarantees outward-facing, consistently wound
    normals (see ``core/mesh.py``), so ``smooth_shading=True`` here produces
    correctly lit organ surfaces instead of the flat/mottled look you get
    from per-face flat shading on a marching-cubes mesh.
  * World coordinates follow the ITK/DICOM convention (X=Left, Y=Posterior,
    Z=Superior for an axis-aligned acquisition), which is already a
    right-handed, Z-up frame — exactly what PyVista/VTK assume by default.
    The camera's view-up is pinned to ``(0, 0, 1)`` explicitly rather than
    left to the default, so the organ never renders sideways regardless of
    which axis PyVista happens to pick as "up" for a given mesh's bounds.
  * The camera is framed from the mesh's own bounding diagonal (not a fixed
    distance), so small organs (kidney) and large ones (lungs) both fill
    the frame instead of appearing as a speck or being clipped.
"""

from __future__ import annotations

import logging
import os

import numpy as np
import trimesh

logger = logging.getLogger(__name__)

ORGAN_COLORS = {
    "lungs": "#E8B4B8",
    "heart": "#B22222",
    "liver": "#8B4513",
    "kidneys": "#800040",
}


def _trimesh_to_pyvista(mesh: trimesh.Trimesh):
    import pyvista as pv

    faces = np.hstack([np.full((len(mesh.faces), 1), 3), mesh.faces]).astype(np.int64)
    return pv.PolyData(mesh.vertices, faces)


def _build_plotter(mesh: trimesh.Trimesh, organ: str, off_screen: bool, window_size: tuple[int, int]):
    import pyvista as pv

    pv_mesh = _trimesh_to_pyvista(mesh)
    plotter = pv.Plotter(off_screen=off_screen, window_size=list(window_size))
    plotter.set_background("#1e1e1e")
    plotter.add_mesh(
        pv_mesh,
        color=ORGAN_COLORS.get(organ.lower(), "#C0C0C0"),
        smooth_shading=True,
        specular=0.3,
        specular_power=15,
        ambient=0.2,
    )
    plotter.add_axes(xlabel="X (L)", ylabel="Y (P)", zlabel="Z (S)")
    plotter.camera.up = (0, 0, 1)

    center = mesh.bounds.mean(axis=0)
    diagonal = float(np.linalg.norm(mesh.bounds[1] - mesh.bounds[0]))
    eye = center + diagonal * np.array([0.9, -0.9, 0.6])
    plotter.camera.position = tuple(eye)
    plotter.camera.focal_point = tuple(center)
    plotter.enable_anti_aliasing()
    return plotter


def render_mesh_interactive(mesh: trimesh.Trimesh, organ: str, window_size: tuple[int, int] = (1024, 768)) -> None:
    """Open an interactive 3D viewer window. Requires a display."""
    plotter = _build_plotter(mesh, organ, off_screen=False, window_size=window_size)
    plotter.show(title=f"Medical3DReconstruction — {organ.capitalize()}")


def render_mesh_screenshot(
    mesh: trimesh.Trimesh,
    organ: str,
    output_path: str,
    window_size: tuple[int, int] = (1024, 768),
) -> str:
    """Render the mesh off-screen to a PNG. Falls back to a Matplotlib
    renderer if no GPU/EGL/OSMesa off-screen context is available (e.g. a
    minimal container without ``libosmesa`` or a virtual display).

    PyVista/VTK is attempted in a **subprocess**, not in-process: a missing
    GPU driver makes VTK's off-screen context creation segfault at the C
    level on some systems, which is not a catchable Python exception — an
    in-process ``try/except`` around it would still crash the caller. Running
    it isolated means a crash there is just a failed subprocess we fall back
    from, not a dead pipeline.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)

    if _try_pyvista_screenshot_subprocess(mesh, organ, output_path, window_size):
        return output_path

    logger.warning(
        "PyVista off-screen rendering unavailable; falling back to Matplotlib "
        "renderer. For full-quality rendering, install libosmesa6 or run "
        "under a display/Xvfb."
    )
    return _render_mesh_screenshot_matplotlib(mesh, organ, output_path, window_size)


def _pyvista_screenshot_worker(
    vertices: np.ndarray, faces: np.ndarray, organ: str, output_path: str, window_size: tuple[int, int]
) -> None:
    """Runs in an isolated subprocess. Must not raise/crash the parent."""
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    plotter = _build_plotter(mesh, organ, off_screen=True, window_size=window_size)
    plotter.screenshot(output_path)
    plotter.close()


def _try_pyvista_screenshot_subprocess(
    mesh: trimesh.Trimesh, organ: str, output_path: str, window_size: tuple[int, int]
) -> bool:
    import multiprocessing

    ctx = multiprocessing.get_context("spawn")
    process = ctx.Process(
        target=_pyvista_screenshot_worker,
        args=(mesh.vertices, mesh.faces, organ, output_path, window_size),
    )
    process.start()
    process.join(timeout=120)

    if process.is_alive():
        process.terminate()
        process.join()
        return False
    return process.exitcode == 0 and os.path.exists(output_path)


def _render_mesh_screenshot_matplotlib(
    mesh: trimesh.Trimesh, organ: str, output_path: str, window_size: tuple[int, int]
) -> str:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    # Matplotlib's Poly3DCollection is a pure-Python software rasterizer —
    # fine for a preview image, but hundreds of thousands of triangles make
    # it prohibitively slow. Cap the triangle count for this fallback path
    # only; the exported STL/OBJ/PLY files keep full resolution.
    preview_mesh = mesh
    max_preview_faces = 20000
    if len(mesh.faces) > max_preview_faces:
        preview_mesh = mesh.simplify_quadric_decimation(face_count=max_preview_faces)

    fig = plt.figure(figsize=(window_size[0] / 100, window_size[1] / 100))
    ax = fig.add_subplot(projection="3d")

    import matplotlib.colors as mcolors

    triangles = preview_mesh.vertices[preview_mesh.faces]
    base_rgb = np.array(mcolors.to_rgb(ORGAN_COLORS.get(organ.lower(), "#C0C0C0")))

    # Matplotlib's built-in `shade=True` path is unreliable across versions
    # when facecolors is a per-face array; compute simple diffuse shading
    # from face normals ourselves instead — fully deterministic, no library
    # quirks to work around.
    light_dir = np.array([0.5, -0.5, 0.7])
    light_dir = light_dir / np.linalg.norm(light_dir)
    normals = preview_mesh.face_normals
    intensity = np.clip(normals @ light_dir, 0.0, 1.0)
    shaded_rgb = base_rgb[None, :] * (0.35 + 0.65 * intensity[:, None])
    facecolors = np.clip(np.hstack([shaded_rgb, np.ones((len(shaded_rgb), 1))]), 0.0, 1.0)

    collection = Poly3DCollection(triangles, facecolors=facecolors, edgecolors="none", shade=False)
    ax.add_collection3d(collection)

    bounds_min, bounds_max = mesh.bounds
    ax.set_xlim(bounds_min[0], bounds_max[0])
    ax.set_ylim(bounds_min[1], bounds_max[1])
    ax.set_zlim(bounds_min[2], bounds_max[2])
    ax.set_box_aspect(bounds_max - bounds_min)
    ax.view_init(elev=20, azim=-60)
    ax.set_xlabel("X (L) mm")
    ax.set_ylabel("Y (P) mm")
    ax.set_zlabel("Z (S) mm")
    ax.set_title(f"Medical3DReconstruction — {organ.capitalize()}")

    fig.savefig(output_path, dpi=100, facecolor="#1e1e1e")
    plt.close(fig)
    return output_path


def show_slice(volume_array: np.ndarray, index: int | None = None, axis: int = 0, output_path: str | None = None):
    """Secondary QA utility: display/save a single 2D slice of the raw volume.

    Not the primary deliverable (3D reconstruction is) — useful for
    eyeballing whether a segmentation mask aligns with the source scan.
    """
    import matplotlib

    if output_path is not None:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if index is None:
        index = volume_array.shape[axis] // 2
    sl = np.take(volume_array, index, axis=axis)

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.imshow(sl, cmap="gray")
    ax.set_title(f"Slice {index} (axis {axis})")
    ax.axis("off")

    if output_path is not None:
        fig.savefig(output_path, dpi=100)
        plt.close(fig)
        return output_path
    plt.show()
    return None
