"""Mesh export to STL, OBJ, and PLY — the three formats the spec requires."""

from __future__ import annotations

import os

import trimesh

SUPPORTED_FORMATS = ("stl", "obj", "ply")


def export_mesh(mesh: trimesh.Trimesh, path: str, file_format: str | None = None) -> str:
    """Export a mesh to STL, OBJ, or PLY.

    Args:
        mesh: The mesh to export.
        path: Destination file path.
        file_format: One of ``SUPPORTED_FORMATS``. Inferred from ``path``'s
            extension if omitted.

    Returns:
        The path written to.
    """
    fmt = (file_format or os.path.splitext(path)[1].lstrip(".")).lower()
    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported export format '{fmt}'. Supported: {SUPPORTED_FORMATS}")

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    mesh.export(path, file_type=fmt)
    return path


def export_all_formats(mesh: trimesh.Trimesh, output_dir: str, base_name: str) -> dict[str, str]:
    """Export a mesh to STL, OBJ, and PLY in one call. Returns format -> path."""
    os.makedirs(output_dir, exist_ok=True)
    paths = {}
    for fmt in SUPPORTED_FORMATS:
        path = os.path.join(output_dir, f"{base_name}.{fmt}")
        paths[fmt] = export_mesh(mesh, path, file_format=fmt)
    return paths
