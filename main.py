#!/usr/bin/env python3
"""Medical3DReconstruction CLI.

Load a CT/MRI (or ex-vivo synchrotron tomography) volume, segment one of
five supported organs (lungs, heart, liver, kidneys, brain) with its
dedicated classical pipeline, reconstruct a 3D mesh, compute geometric
metrics, validate the result, and export STL/OBJ/PLY.

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
from medical3d.core.html_viewer import export_interactive_viewer  # noqa: E402
from medical3d.core.visualization import render_mesh_interactive, render_mesh_screenshot  # noqa: E402
from medical3d.io import VolumeLoadError, load_volume  # noqa: E402
from medical3d.organs import ORGAN_PIPELINES  # noqa: E402

DEFAULT_CONFIG_PATHS = {
    organ: os.path.join(_REPO_ROOT, "configs", f"{organ}.yaml") for organ in ORGAN_PIPELINES
}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Reconstruye la malla 3D de un órgano (pulmones, corazón, hígado, "
            "riñones, cerebro) a partir de un volumen CT/MRI o de tomografía "
            "sincrotrón ex-vivo: segmentación, generación de malla, métricas, "
            "validación y exportación STL/OBJ/PLY."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Ruta a un archivo de volumen (.nrrd/.nii/.nii.gz/.mha/.mhd) o a un directorio con una serie DICOM",
    )
    parser.add_argument(
        "--organ", required=True, choices=sorted(ORGAN_PIPELINES), help="Órgano a segmentar y reconstruir"
    )
    parser.add_argument(
        "--modality",
        default="CT",
        choices=["CT", "MRI", "synchrotron"],
        help=(
            "Modalidad de imagen (por defecto: CT). 'synchrotron' es para "
            "archivos de tomografía de contraste de fase ex-vivo (p. ej. "
            "ESRF Human Organ Atlas / HiP-CT), distribuidos como un "
            "directorio o .zip de imágenes de cortes 2D en lugar de "
            "DICOM/NIfTI — requiere --spacing."
        ),
    )
    parser.add_argument(
        "--spacing",
        nargs=3,
        type=float,
        default=None,
        metavar=("SX", "SY", "SZ"),
        help="Espaciado de vóxel en mm (x y z), obligatorio con --modality synchrotron",
    )
    parser.add_argument(
        "--config", default=None, help="Ruta a un YAML de configuración del órgano (por defecto: configs/<organ>.yaml)"
    )
    parser.add_argument(
        "--output-dir", default="outputs", help="Directorio para las mallas y previsualizaciones exportadas (por defecto: outputs)"
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        default=["stl", "obj", "ply"],
        choices=["stl", "obj", "ply"],
        help="Formatos de exportación de malla (por defecto: los tres)",
    )
    parser.add_argument(
        "--visualize",
        choices=["interactive", "screenshot", "html", "none"],
        default="screenshot",
        help=(
            "Modo de visualización 3D: una ventana interactiva, una "
            "previsualización PNG renderizada, un visor HTML autocontenido "
            "(malla 3D + explorador de cortes CT, sin servidor ni "
            "instalación), o ninguno (por defecto: screenshot)"
        ),
    )
    parser.add_argument(
        "--metrics-json", default=None, help="Ruta opcional para además escribir métricas + validación en JSON"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    if args.modality == "synchrotron" and args.spacing is None:
        print("ERROR: --modality synchrotron requiere --spacing SX SY SZ (mm)", file=sys.stderr)
        return 1

    if args.organ == "brain" and args.modality != "synchrotron":
        print(
            "ERROR: --organ brain solo admite --modality synchrotron "
            "(tomografía ex-vivo) — este proyecto no incluye un pipeline clínico CT/MRI para cerebro.",
            file=sys.stderr,
        )
        return 1

    default_config_path = DEFAULT_CONFIG_PATHS[args.organ]
    if args.modality == "synchrotron":
        synchrotron_config = os.path.join(_REPO_ROOT, "configs", f"{args.organ}_synchrotron.yaml")
        if os.path.exists(synchrotron_config):
            default_config_path = synchrotron_config
    config_path = args.config or default_config_path

    print("=" * 60)
    print("Medical3DReconstruction")
    print("=" * 60)

    print(f"\nÓrgano: {args.organ}")
    print(f"Configuración: {config_path}")
    try:
        config = load_organ_config(config_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    # Some archives (e.g. the liver overview scan, ~1.6 billion voxels) are
    # too large to decode at native resolution before any downsampling
    # runs — load_stride skips slices/pixels *while decoding* instead of
    # after, so the config is read before the volume is loaded.
    load_stride = config.get("load_stride", 1) if args.modality == "synchrotron" else 1

    print(f"\nCargando volumen: {args.input}")
    try:
        volume = load_volume(
            args.input,
            modality=args.modality,
            spacing_mm=tuple(args.spacing) if args.spacing else None,
            load_stride=load_stride,
        )
    except VolumeLoadError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"  forma (z,y,x) = {volume.array.shape}, espaciado (mm) = {volume.spacing}, modalidad = {volume.modality}")

    pipeline = ORGAN_PIPELINES[args.organ](config)

    print("\nEjecutando pipeline (preprocesamiento -> segmentación -> postprocesamiento -> malla -> optimización -> validación)...")
    result = pipeline.run(volume)

    print("\n" + "-" * 60)
    print("MÉTRICAS DE RECONSTRUCCIÓN")
    print("-" * 60)
    metrics_dict = result.metrics.as_dict()
    for key, value in metrics_dict.items():
        print(f"  {key:22s}: {value}")

    print("\n" + "-" * 60)
    print("VALIDACIÓN")
    print("-" * 60)
    validation_dict = result.validation.as_dict()
    for key, value in validation_dict.items():
        print(f"  {key:22s}: {value}")
    if not result.validation.passed:
        print("\n  ADVERTENCIA: la validación no fue exitosa. Revisa la máscara/malla antes de confiar en estos resultados.")

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"\nExportando malla a '{args.output_dir}/' ({', '.join(args.formats)})...")
    for fmt in args.formats:
        path = os.path.join(args.output_dir, f"{args.organ}.{fmt}")
        export_mesh(result.mesh, path, file_format=fmt)
        print(f"  {fmt.upper():4s} -> {path}")

    if args.metrics_json:
        with open(args.metrics_json, "w") as f:
            json.dump({"metrics": metrics_dict, "validation": validation_dict}, f, indent=2)
        print(f"\nMétricas escritas en {args.metrics_json}")

    if args.visualize == "interactive":
        print("\nAbriendo visor 3D interactivo...")
        render_mesh_interactive(result.mesh, args.organ)
    elif args.visualize == "screenshot":
        screenshot_path = os.path.join(args.output_dir, f"{args.organ}_preview.png")
        print(f"\nRenderizando previsualización 3D en {screenshot_path}...")
        render_mesh_screenshot(result.mesh, args.organ, screenshot_path)
        print(f"  -> {screenshot_path}")
    elif args.visualize == "html":
        viewer_path = os.path.join(args.output_dir, f"{args.organ}_viewer.html")
        print(f"\nExportando visor HTML interactivo a {viewer_path}...")
        export_interactive_viewer(
            organ=args.organ,
            mesh=result.mesh,
            metrics=result.metrics,
            validation=result.validation,
            volume=result.volume,
            output_path=viewer_path,
        )
        print(f"  -> {viewer_path} (ábrelo en cualquier navegador, sin necesidad de servidor)")

    print("\nListo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
