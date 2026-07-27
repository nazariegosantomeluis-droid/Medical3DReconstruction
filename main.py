#!/usr/bin/env python3
"""Medical3DReconstruction CLI.

Load a CT/MRI volume, segment one of four supported organs (lungs, heart,
liver, kidneys) with its dedicated classical pipeline, reconstruct a 3D
mesh, compute geometric metrics, validate the result, and export STL/OBJ/PLY.

Usage:
    python main.py --input data/volumes/CTChest.nrrd --organ lungs
    python main.py --input path/to/dicom_series/ --organ heart --modality CT --visualize interactive
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
_SRC_PATH = os.path.join(_REPO_ROOT, "src")
if _SRC_PATH not in sys.path:
    sys.path.insert(0, _SRC_PATH)

from medical3d.core.config import load_organ_config  # noqa: E402
from medical3d.core.exporters import export_mesh  # noqa: E402
from medical3d.core.visualization import render_mesh_interactive, render_mesh_screenshot  # noqa: E402
from medical3d.io import VolumeLoadError, load_volume  # noqa: E402
from medical3d.organs import ORGAN_PIPELINES  # noqa: E402

DEFAULT_CONFIG_PATHS = {
    organ: os.path.join(_REPO_ROOT, "configs", f"{organ}.yaml") for organ in ORGAN_PIPELINES
}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Reconstruct a 3D mesh of one organ (lungs, heart, liver, "
            "kidneys) from a CT/MRI volume: segmentation, meshing, metrics, "
            "validation, and STL/OBJ/PLY export."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to a volume file (.nrrd/.nii/.nii.gz/.mha/.mhd) or a directory containing one DICOM series",
    )
    parser.add_argument(
        "--organ", required=True, choices=sorted(ORGAN_PIPELINES), help="Organ to segment and reconstruct"
    )
    parser.add_argument("--modality", default="CT", choices=["CT", "MRI"], help="Imaging modality (default: CT)")
    parser.add_argument(
        "--config", default=None, help="Path to an organ config YAML (default: configs/<organ>.yaml)"
    )
    parser.add_argument(
        "--output-dir", default="outputs", help="Directory for exported meshes and previews (default: outputs)"
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        default=["stl", "obj", "ply"],
        choices=["stl", "obj", "ply"],
        help="Mesh export formats (default: all three)",
    )
    parser.add_argument(
        "--visualize",
        choices=["interactive", "screenshot", "none"],
        default="screenshot",
        help="3D visualization mode: an interactive viewer window, a rendered PNG preview, or skip (default: screenshot)",
    )
    parser.add_argument(
        "--metrics-json", default=None, help="Optional path to also write metrics + validation as JSON"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    config_path = args.config or DEFAULT_CONFIG_PATHS[args.organ]

    print("=" * 60)
    print("Medical3DReconstruction")
    print("=" * 60)

    print(f"\nLoading volume: {args.input}")
    try:
        volume = load_volume(args.input, modality=args.modality)
    except VolumeLoadError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"  shape (z,y,x) = {volume.array.shape}, spacing (mm) = {volume.spacing}, modality = {volume.modality}")

    print(f"\nOrgan: {args.organ}")
    print(f"Config: {config_path}")
    try:
        config = load_organ_config(config_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    pipeline = ORGAN_PIPELINES[args.organ](config)

    print("\nRunning pipeline (preprocess -> segment -> postprocess -> mesh -> optimize -> validate)...")
    result = pipeline.run(volume)

    print("\n" + "-" * 60)
    print("RECONSTRUCTION METRICS")
    print("-" * 60)
    metrics_dict = result.metrics.as_dict()
    for key, value in metrics_dict.items():
        print(f"  {key:22s}: {value}")

    print("\n" + "-" * 60)
    print("VALIDATION")
    print("-" * 60)
    validation_dict = result.validation.as_dict()
    for key, value in validation_dict.items():
        print(f"  {key:22s}: {value}")
    if not result.validation.passed:
        print("\n  WARNING: validation did not pass. Inspect the mask/mesh before trusting these results.")

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"\nExporting mesh to '{args.output_dir}/' ({', '.join(args.formats)})...")
    for fmt in args.formats:
        path = os.path.join(args.output_dir, f"{args.organ}.{fmt}")
        export_mesh(result.mesh, path, file_format=fmt)
        print(f"  {fmt.upper():4s} -> {path}")

    if args.metrics_json:
        with open(args.metrics_json, "w") as f:
            json.dump({"metrics": metrics_dict, "validation": validation_dict}, f, indent=2)
        print(f"\nMetrics written to {args.metrics_json}")

    if args.visualize == "interactive":
        print("\nOpening interactive 3D viewer...")
        render_mesh_interactive(result.mesh, args.organ)
    elif args.visualize == "screenshot":
        screenshot_path = os.path.join(args.output_dir, f"{args.organ}_preview.png")
        print(f"\nRendering 3D preview to {screenshot_path}...")
        render_mesh_screenshot(result.mesh, args.organ, screenshot_path)
        print(f"  -> {screenshot_path}")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
