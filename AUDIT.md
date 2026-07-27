# Repository Audit — Pre-Rebuild

This document records the file-by-file audit performed before the ground-up
rebuild of Medical3DReconstruction. The prior repository consisted of two
commits and a minimal skeleton — there was no segmentation, no meshing, no
metrics, no export, and no organ-specific logic of any kind. Every decision
below follows one rule: **code is kept only if it is architecturally correct
for the target system, never because it already exists.**

| File | Verdict | Reasoning |
|---|---|---|
| `main.py` | **DELETE** | Hard-coded to one file path (`data/volumes/CTChest.nrrd`), no organ selection, no segmentation/meshing/export — just a demo of loading + printing + plotting a slice. Replaced by a real CLI (`main.py`) that drives the organ pipelines. |
| `src/io/load_volume.py` | **DELETE** | `sitk.ReadImage(path)` with an existence check is not a loader — it silently fails on DICOM series (a directory, not a file), does no modality/orientation validation, and returns a bare `sitk.Image` with no reproducibility metadata. Replaced by `medical3d/io/volume_loader.py` + a `Volume` value object. |
| `src/analysis/volume_info.py` | **DELETE** | Prints raw SimpleITK metadata (size/spacing/origin/direction/pixel type). This is diagnostic scaffolding, not the volume/surface-area/centroid/bbox/vertex/triangle metrics the spec requires, and it operates on the raw scan rather than the segmented organ. Superseded by `medical3d/core/mesh.py::MeshMetrics`. |
| `src/visualization/show_slice.py` | **DELETE** | 2D matplotlib slice viewer only. The spec requires 3D reconstruction visualization. No 3D rendering existed anywhere in the repo. Replaced by `medical3d/core/visualization.py` (3D mesh rendering via PyVista, with a slice-viewer utility kept only as a secondary QA aid, not the primary output). |
| `src/preprocessing/__init__.py` | **DELETE** | Empty (0 bytes). No preprocessing logic existed. A single shared `preprocessing` module would also violate the "no shared segmentation algorithm across organs" requirement — preprocessing is now per-organ. |
| `src/segmentation/__init__.py` | **DELETE** | Empty (0 bytes). No segmentation algorithm of any kind existed — classical or otherwise. A shared segmentation package is explicitly disallowed by the spec (each organ needs an independent pipeline), so this location is architecturally wrong even as an empty stub. |
| `src/reconstruction/__init__.py` | **DELETE** | Empty (0 bytes). No mesh generation existed. |
| `src/export/__init__.py` | **DELETE** | Empty (0 bytes). No STL/OBJ/PLY export existed. |
| `src/analysis/__init__.py`, `src/io/__init__.py`, `src/visualization/__init__.py`, `src/__init__.py` | **DELETE** | Empty package markers for a package layout that is being replaced outright (flat `src/<concern>` instead of a proper `medical3d` package with `organs/<name>/{preprocessing,segmentation,postprocessing,pipeline,config}`). |
| `README.md` | **REWRITE** | 0 bytes — never written. Replaced with real scope, architecture, algorithm rationale, and usage docs. |
| `requirements.txt` | **REWRITE** | 0 bytes — never written. Replaced with pinned, verified-installable dependencies (SimpleITK, numpy, scipy, scikit-image, trimesh, PyVista, PyYAML, pytest). |
| `LICENSE` | **REWRITE** | 0 bytes — a license file that grants no rights. Replaced with a complete MIT license text. |
| `.gitignore` | **KEEP** | Correct and minimal (`__pycache__/`, `*.py[cod]`, `*.so`, `*.pyd`). Extended with build/venv/export-artifact/OS-cruft patterns, but the original rules are valid and kept. |
| `data/volumes/CTChest.nrrd` | **KEEP** | Real chest CT (512×512×139, 0.76×0.76×2.5 mm spacing, signed 16/32-bit HU, range −3024…3071). Genuinely useful as an integration-test fixture for the lung and heart pipelines — this is the only real scan in the repo and there is no reason to discard real data. |
| `src/__pycache__/*`, `src/*/__pycache__/*` | **DELETE** | Build artifacts, should never have been committed. Removed and `.gitignore` already excludes them going forward. |

## Summary

Nothing in the previous repository was architecturally reusable: there was
no segmentation, no meshing, no metrics, no export, and no organ concept at
all — only a loader, a metadata printer, and a slice viewer wired to one
hard-coded file. The rebuild keeps only the two genuinely reusable assets:
the sample CT volume (as a test fixture) and the `.gitignore` rules. Every
line of Python is new.
