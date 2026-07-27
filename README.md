# Medical3DReconstruction

Reconstruct a validated 3D surface mesh of one organ — **lungs, heart,
liver, or kidneys** — from a CT or MRI volume, using an independent
classical (non-learned) segmentation pipeline per organ.

```
CT/MRI volume  →  organ-specific segmentation  →  3D mesh  →  metrics + validation  →  STL / OBJ / PLY
```

## Scope

This project does exactly one thing: turn a single CT/MRI volume into a
3D-printable, metrically-validated mesh of one of four organs. It is
deliberately **not**:

- a PACS or DICOM viewer,
- an AI/deep-learning segmentation platform,
- a 3D Slicer-style general image processing suite,
- a multi-organ atlas or registration framework.

There is no shared, generic "segment(organ)" function. Lungs, heart,
liver, and kidneys have four independent pipelines because they fail
under a one-size-fits-all approach — see [`docs/ORGAN_PIPELINES.md`](docs/ORGAN_PIPELINES.md)
for why each organ needs the algorithm it uses.

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python main.py --input data/volumes/CTChest.nrrd --organ lungs
```

This loads the volume, runs the lung pipeline (preprocess → segment →
postprocess → mesh → optimize → validate), prints the metrics and
validation report, exports `outputs/lungs.{stl,obj,ply}`, and renders a
preview to `outputs/lungs_preview.png`.

```bash
python main.py --input <volume-or-dicom-dir> --organ {lungs,heart,liver,kidneys} \
    [--modality {CT,MRI}] \
    [--config configs/<organ>.yaml] \
    [--output-dir outputs] \
    [--formats stl obj ply] \
    [--visualize {interactive,screenshot,none}] \
    [--metrics-json outputs/<organ>_metrics.json]
```

`--input` accepts a single volume file (`.nrrd`, `.nii`, `.nii.gz`, `.mha`,
`.mhd`) or a directory containing one DICOM series.

## What gets computed

For the reconstructed mesh:

- **Volume** (mm³ and mL) — from the mesh's signed geometry, not a voxel
  count, so it reflects what's actually exported.
- **Surface area** (mm²)
- **Centroid** (mm, patient physical space)
- **Bounding box** (mm, min/max corners)
- **Vertex count** and **triangle count**

Plus a validation report: mesh watertightness/winding consistency,
a literature-informed anatomical volume plausibility check, and (when a
ground-truth mask is available) Dice, Jaccard, and surface distance.

## Architecture

```
main.py                      CLI: load → select organ → run → report → export → visualize
src/medical3d/
  io/                         Volume loading (DICOM series, NRRD/NIfTI/MHA) + validation
  core/
    volume.py                 Volume: array + spacing/origin/direction, physical-space math
    config.py                 YAML organ configuration
    preprocessing_utils.py     Generic image ops shared across organs (resample, denoise, ROI crop)
    mesh.py                    Marching cubes, mesh metrics
    mesh_ops.py                Smoothing, decimation, repair, quality assessment
    validation.py               Dice/Jaccard/surface distance, plausibility ranges
    exporters.py                STL/OBJ/PLY export
    visualization.py            3D rendering (PyVista, with a Matplotlib fallback)
  organs/
    base.py                    OrganPipeline ABC: preprocess → segment → postprocess → mesh → optimize → validate
    lungs/                      threshold + connected components
    heart/                      boundary-aware geodesic active contour level set
    liver/                      seeded confidence-connected region growing
    kidneys/                    bilateral boundary-aware geodesic active contour level set
configs/<organ>.yaml           Per-organ parameters (thresholds, ROI priors, mesh settings)
tests/                         Real-CT and synthetic-phantom pipeline tests, geometry unit tests
docs/                          Architecture rationale, per-organ algorithm writeups, validation methodology
```

Generic geometry code (marching cubes, mesh smoothing/decimation, export,
plausibility checks) is shared through `core/`, because it's library-grade
math with no organ-specific decisions in it. **Segmentation is not
shared** — each organ's `segmentation.py` is independently implemented
and tuned; see [`AUDIT.md`](AUDIT.md) and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
for the reasoning.

## Why each organ uses the algorithm it uses

| Organ | Approach | Why |
|---|---|---|
| Lungs | Body-masked HU threshold + connected components | Aerated lung is >500 HU separated from all surrounding tissue — a global threshold is sufficient once background air is excluded via a body mask. |
| Heart | Boundary-aware geodesic active contour level set | Myocardium/blood pool HU overlaps the great vessels, pericardial fat, and diaphragm — a threshold leaks; the level set stops at image gradients (edges), not intensity. |
| Liver | Seeded confidence-connected region growing | Liver parenchyma is homogeneous but not intensity-unique (overlaps spleen/kidney/muscle) — region growing from a right-upper-quadrant seed, adapting to local statistics, contains the leak. |
| Kidneys | Bilateral boundary-aware geodesic active contour level set | Same overlap problem as the heart (renal parenchyma vs. psoas muscle), run independently from two seeds for the two kidneys. |

Full rationale, parameters, and known limitations for each organ are in
[`docs/ORGAN_PIPELINES.md`](docs/ORGAN_PIPELINES.md).

## Validation

- **Lungs and heart** are validated end-to-end against a real chest CT
  (`data/volumes/CTChest.nrrd`, included in this repo) — plausible
  anatomical volume, watertight mesh, single connected body.
- **Liver and kidneys** are validated against synthetic phantoms (see
  `tests/conftest.py`), because this repository does not ship an
  abdominal CT fixture. The phantom tests confirm pipeline *mechanics*
  (segmentation converges, mesh is watertight, most of the known
  synthetic volume is recovered) — they are not a substitute for
  validation against expert-labeled clinical data.
- Prior work on this project measured Dice 0.918 (liver) and Dice 0.862
  (lung) against expert-labeled data; those are the reference points the
  segmentation *approach* for each organ was chosen to reproduce, not a
  claim about this exact codebase without re-running against that
  labeled data. See [`docs/VALIDATION.md`](docs/VALIDATION.md) for how to
  validate against your own ground-truth masks.

## Testing

```bash
pytest
```

30 tests: mesh geometry correctness against closed-form sphere volume/
surface-area/centroid, mesh operations (smoothing, decimation, repair),
STL/OBJ/PLY export round-trips, Dice/Jaccard/plausibility validation
logic, volume I/O, and all four organ pipelines end-to-end (lungs/heart
against the real CT fixture, liver/kidneys against synthetic phantoms).

## 3D visualization notes

Rendering uses PyVista/VTK by default. World coordinates follow the
ITK/DICOM convention (X=Left, Y=Posterior, Z=Superior for an axis-aligned
acquisition), which is already a right-handed, Z-up frame — the camera's
view-up is pinned to `(0, 0, 1)` so organs never render sideways, and
`--visualize interactive` opens a real interactive window. Mesh normals
are always outward-facing (`trimesh.repair.fix_normals` runs
unconditionally after marching cubes), which is what makes a reconstructed
organ render correctly lit instead of appearing matte-black/"inside out."

In headless environments without a GPU/EGL/OSMesa context, `--visualize
screenshot` automatically falls back to a Matplotlib-rendered preview
(the fallback runs the risky PyVista attempt in an isolated subprocess
first, since a missing off-screen driver can segfault VTK at the C level).

## License

MIT — see [`LICENSE`](LICENSE).
