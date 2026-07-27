"""STL/OBJ/PLY export round-trips."""

from __future__ import annotations

import os

import trimesh

from medical3d.core.exporters import export_all_formats, export_mesh


def test_export_all_formats_writes_all_three(tmp_path):
    mesh = trimesh.creation.icosphere(subdivisions=2, radius=5.0)
    paths = export_all_formats(mesh, str(tmp_path), "test_organ")

    assert set(paths.keys()) == {"stl", "obj", "ply"}
    for fmt, path in paths.items():
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0
        reloaded = trimesh.load(path, force="mesh")
        assert len(reloaded.vertices) > 0
        assert len(reloaded.faces) == len(mesh.faces)


def test_export_mesh_infers_format_from_extension(tmp_path):
    mesh = trimesh.creation.icosphere(subdivisions=1, radius=5.0)
    path = str(tmp_path / "organ.stl")
    export_mesh(mesh, path)
    assert os.path.exists(path)


def test_export_mesh_rejects_unsupported_format(tmp_path):
    import pytest

    mesh = trimesh.creation.icosphere(subdivisions=1, radius=5.0)
    with pytest.raises(ValueError):
        export_mesh(mesh, str(tmp_path / "organ.glb"))
