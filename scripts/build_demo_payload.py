#!/usr/bin/env python3
"""Build the per-organ payload (decimated mesh + downsampled slice cube +
metrics + validation) used by the published interactive HTML demo.

This is a standalone dev utility, not part of the CLI pipeline: the CLI's
own single-organ export (``main.py --visualize html``, backed by
``medical3d.core.html_viewer``) is the "real" reproducible output. This
script instead builds a *combined, multi-organ* payload sized to fit the
16MB artifact-publishing limit, by aggressively downsampling every organ's
slice cube and decimating its mesh far harder than the CLI export does.

Usage:
    python scripts/build_demo_payload.py --output /path/to/payload.json

Requires the real organ archives under data/organ_atlas/ (see
docs/ORGAN_PIPELINES.md) and data/volumes/CTChest.nrrd for lungs. Each
organ's mesh is read from outputs/<organ>.stl (already exported by a prior
``python main.py --organ <organ> ...`` run) and re-decimated for the
browser; each organ's slice cube is regenerated from the source volume by
re-running only that organ's ``preprocess`` step (cheap relative to a full
segmentation run) so the slices shown match what the pipeline actually
segmented, not the raw un-cropped archive.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC_PATH = os.path.join(_REPO_ROOT, "src")
if _SRC_PATH not in sys.path:
    sys.path.insert(0, _SRC_PATH)

import numpy as np  # noqa: E402
import trimesh  # noqa: E402

from medical3d.core.config import load_organ_config  # noqa: E402
from medical3d.core.mesh_ops import decimate_mesh  # noqa: E402
from medical3d.io import load_volume  # noqa: E402
from medical3d.organs.brain.preprocessing import preprocess as brain_preprocess  # noqa: E402
from medical3d.organs.heart.preprocessing import preprocess as heart_preprocess  # noqa: E402
from medical3d.organs.kidneys.preprocessing import preprocess as kidneys_preprocess  # noqa: E402
from medical3d.organs.liver.preprocessing import preprocess as liver_preprocess  # noqa: E402
from medical3d.organs.lungs.preprocessing import preprocess as lungs_preprocess  # noqa: E402

_MAX_DEMO_FACES = 30000
_MAX_SLICE_EDGE_PX = 90
_MAX_SLICE_DEPTH = 110

ORGAN_COLORS = {
    "lungs": "#e8b4b8",
    "heart": "#c0392b",
    "liver": "#b9793f",
    "kidneys": "#a8447a",
    "brain": "#c9a0dc",
}


def _pack_mesh(stl_path: str) -> dict:
    mesh = trimesh.load(stl_path, process=True)
    if len(mesh.faces) > _MAX_DEMO_FACES:
        mesh = decimate_mesh(mesh, target_face_fraction=_MAX_DEMO_FACES / len(mesh.faces))
    mesh = mesh.copy()
    mesh.fix_normals()
    verts = mesh.vertices.astype(np.float32)
    norms = mesh.vertex_normals.astype(np.float32)
    faces = mesh.faces.astype(np.uint32)
    return {
        "positions_b64": base64.b64encode(verts.tobytes()).decode("ascii"),
        "normals_b64": base64.b64encode(norms.tobytes()).decode("ascii"),
        "indices_b64": base64.b64encode(faces.tobytes()).decode("ascii"),
        "center": verts.mean(axis=0).tolist(),
        "num_vertices": int(len(mesh.vertices)),
        "num_triangles": int(len(mesh.faces)),
    }


def _pack_slices(array: np.ndarray, spacing, origin) -> dict:
    nz, ny, nx = array.shape
    stride_z = max(1, round(nz / _MAX_SLICE_DEPTH))
    stride_y = max(1, round(ny / _MAX_SLICE_EDGE_PX))
    stride_x = max(1, round(nx / _MAX_SLICE_EDGE_PX))
    small = array[::stride_z, ::stride_y, ::stride_x]

    lo = float(np.percentile(small, 0.5))
    hi = float(np.percentile(small, 99.5))
    if hi <= lo:
        hi = lo + 1.0
    quantized = np.clip((small.astype(np.float32) - lo) / (hi - lo) * 255.0, 0, 255).astype(np.uint8)

    sx, sy, sz = spacing
    return {
        "shape_zyx": list(quantized.shape),
        "spacing_xyz": [sx * stride_x, sy * stride_y, sz * stride_z],
        "origin_xyz": list(origin),
        "value_min": lo,
        "value_max": hi,
        "voxels_b64": base64.b64encode(quantized.tobytes()).decode("ascii"),
    }


def _metrics_and_validation(metrics_json_path: str) -> tuple[dict, dict]:
    with open(metrics_json_path) as f:
        data = json.load(f)
    return data["metrics"], data["validation"]


def _build_lungs() -> dict:
    volume = load_volume(os.path.join(_REPO_ROOT, "data", "volumes", "CTChest.nrrd"), modality="CT")
    config = load_organ_config(os.path.join(_REPO_ROOT, "configs", "lungs.yaml"))
    pre = lungs_preprocess(volume, config)
    return {
        "mesh": _pack_mesh(os.path.join(_REPO_ROOT, "outputs", "lungs.stl")),
        "slices": _pack_slices(pre.array, pre.spacing, pre.origin),
    }


def _build_heart() -> dict:
    volume = load_volume(
        os.path.join(_REPO_ROOT, "data", "organ_atlas", "heart_LADAF-2021-17_169um.zip"),
        modality="synchrotron",
        spacing_mm=(0.16936, 0.16936, 0.16936),
    )
    config = load_organ_config(os.path.join(_REPO_ROOT, "configs", "heart_synchrotron.yaml"))
    pre = heart_preprocess(volume, config)
    return {
        "mesh": _pack_mesh(os.path.join(_REPO_ROOT, "outputs", "heart.stl")),
        "slices": _pack_slices(pre.array, pre.spacing, pre.origin),
    }


def _build_brain() -> dict:
    volume = load_volume(
        os.path.join(_REPO_ROOT, "data", "organ_atlas", "brain_LADAF-2021-17_169um.zip"),
        modality="synchrotron",
        spacing_mm=(0.1696, 0.1696, 0.1696),
    )
    config = load_organ_config(os.path.join(_REPO_ROOT, "configs", "brain_synchrotron.yaml"))
    pre = brain_preprocess(volume, config)
    return {
        "mesh": _pack_mesh(os.path.join(_REPO_ROOT, "outputs", "brain.stl")),
        "slices": _pack_slices(pre.array, pre.spacing, pre.origin),
    }


def _build_kidneys() -> dict:
    volume = load_volume(
        os.path.join(_REPO_ROOT, "data", "organ_atlas", "kidney_K292_163um.zip"),
        modality="synchrotron",
        spacing_mm=(0.16352, 0.16352, 0.16352),
    )
    config = load_organ_config(os.path.join(_REPO_ROOT, "configs", "kidneys_synchrotron.yaml"))
    pre = kidneys_preprocess(volume, config)
    return {
        "mesh": _pack_mesh(os.path.join(_REPO_ROOT, "outputs", "kidneys.stl")),
        "slices": _pack_slices(pre.array, pre.spacing, pre.origin),
    }


def _build_liver() -> dict:
    config = load_organ_config(os.path.join(_REPO_ROOT, "configs", "liver_synchrotron.yaml"))
    volume = load_volume(
        os.path.join(_REPO_ROOT, "data", "organ_atlas", "liver_LADAF-2021-17_180um.zip"),
        modality="synchrotron",
        spacing_mm=(0.18048, 0.18048, 0.18048),
        load_stride=config.get("load_stride", 1),
    )
    pre = liver_preprocess(volume, config)
    return {
        "mesh": _pack_mesh(os.path.join(_REPO_ROOT, "outputs", "liver.stl")),
        "slices": _pack_slices(pre.array, pre.spacing, pre.origin),
    }


_BUILDERS = {
    "lungs": _build_lungs,
    "heart": _build_heart,
    "liver": _build_liver,
    "kidneys": _build_kidneys,
    "brain": _build_brain,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="Path to write the combined JSON payload to")
    parser.add_argument(
        "--organs", nargs="+", default=sorted(_BUILDERS), choices=sorted(_BUILDERS), help="Which organs to build"
    )
    args = parser.parse_args()

    payload = {}
    for organ in args.organs:
        print(f"Building payload for {organ}...", file=sys.stderr)
        built = _BUILDERS[organ]()
        metrics_path = os.path.join(_REPO_ROOT, "outputs", f"{organ}_metrics.json")
        if os.path.exists(metrics_path):
            metrics, validation = _metrics_and_validation(metrics_path)
        else:
            metrics, validation = None, None
        payload[organ] = {
            "color": ORGAN_COLORS[organ],
            "mesh": built["mesh"],
            "slices": built["slices"],
            "metrics": metrics,
            "validation": validation,
        }
        approx_kb = (len(built["mesh"]["positions_b64"]) + len(built["slices"]["voxels_b64"])) // 1024
        print(f"  {organ}: ~{approx_kb} KB", file=sys.stderr)

    with open(args.output, "w") as f:
        json.dump(payload, f)
    total_mb = os.path.getsize(args.output) / (1024 * 1024)
    print(f"Wrote {args.output} ({total_mb:.2f} MB)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
