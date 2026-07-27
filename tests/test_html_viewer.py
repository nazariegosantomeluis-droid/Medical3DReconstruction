"""Self-contained interactive HTML export."""

from __future__ import annotations

import os

import trimesh

from medical3d.core.html_viewer import export_interactive_viewer
from medical3d.core.mesh import compute_mesh_metrics
from medical3d.core.mesh_ops import MeshQualityReport
from medical3d.core.validation import validate_segmentation
from medical3d.core.volume import Volume


def test_export_interactive_viewer_writes_self_contained_html(tmp_path, sphere_volume):
    mask, volume, _v, _a, _c = sphere_volume
    mesh = trimesh.creation.icosphere(subdivisions=3, radius=20.0)
    metrics = compute_mesh_metrics(mesh)
    quality = MeshQualityReport(is_watertight=True, is_winding_consistent=True, euler_number=2, num_bodies=1)
    validation = validate_segmentation(organ="heart", volume_ml=metrics.volume_ml, mesh_quality=quality)

    output_path = str(tmp_path / "viewer.html")
    result_path = export_interactive_viewer(
        organ="heart", mesh=mesh, metrics=metrics, validation=validation, volume=volume, output_path=output_path
    )

    assert result_path == output_path
    assert os.path.exists(output_path)
    assert os.path.getsize(output_path) > 10_000

    with open(output_path) as f:
        html = f.read()

    # No external resources — must be usable offline with no server.
    assert "<script src=" not in html
    assert "http://" not in html.replace("http://www.w3.org", "")
    assert "cdn." not in html.lower()
    assert "PAYLOAD" in html
    assert "webgl" in html.lower()


def test_export_interactive_viewer_creates_output_directory(tmp_path, sphere_volume):
    _mask, volume, _v, _a, _c = sphere_volume
    mesh = trimesh.creation.icosphere(subdivisions=2, radius=10.0)
    metrics = compute_mesh_metrics(mesh)
    quality = MeshQualityReport(is_watertight=True, is_winding_consistent=True, euler_number=2, num_bodies=1)
    validation = validate_segmentation(organ="liver", volume_ml=metrics.volume_ml, mesh_quality=quality)

    nested_path = str(tmp_path / "nested" / "dir" / "viewer.html")
    export_interactive_viewer(
        organ="liver", mesh=mesh, metrics=metrics, validation=validation, volume=volume, output_path=nested_path
    )
    assert os.path.exists(nested_path)
