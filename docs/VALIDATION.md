# Validation methodology

Every pipeline run produces a `ValidationReport` (`core/validation.py`),
combining three independent checks:

## 1. Mesh quality

`core/mesh_ops.py::assess_mesh_quality` reports:

- `is_watertight` — every edge shared by exactly two faces. A
  non-watertight mesh has an ill-defined enclosed volume and may not
  slice/3D-print correctly.
- `is_winding_consistent` — face normals agree on inside/outside.
- `euler_number`, `num_bodies` — sanity signals for unexpected topology
  (a lung mesh with 6 disconnected bodies likely has segmentation noise
  that survived postprocessing).

`ValidationReport.passed` requires `is_watertight` and a plausible volume
(see below); it does **not** require single-body meshes, since lungs and
kidneys are legitimately bilateral.

## 2. Anatomical plausibility

`PLAUSIBLE_VOLUME_RANGES_ML` in `core/validation.py` holds wide,
literature-informed adult reference ranges:

| Organ | Range (mL) |
|---|---|
| Lungs | 2000–7000 |
| Heart | 300–900 |
| Liver | 1000–2500 |
| Kidneys (both) | 200–450 |

These ranges span normal physiological variation (not just measurement
noise) — the point is to catch gross segmentation failures (leakage into
a neighboring structure, capturing only a fragment), not to grade
accuracy. A result outside this range is a **warning to investigate**,
not proof the segmentation is wrong (real anatomy varies, especially at
the extremes of body size).

## 3. Overlap against ground truth (optional)

`compute_overlap_metrics(prediction, ground_truth, spacing)` computes:

- **Dice coefficient** and **Jaccard index** (voxel overlap).
- **Mean and Hausdorff surface distance** (mm), from boundary voxels of
  each mask via a KD-tree nearest-neighbor query in physical space.

This is how the Dice scores referenced in this project's design notes —
liver 0.918, lung 0.862 — were originally measured, and how you should
validate this codebase against your own expert-labeled data:

```python
from medical3d.core.validation import compute_overlap_metrics

overlap = compute_overlap_metrics(predicted_mask, ground_truth_mask, spacing=volume.spacing)
print(overlap.dice, overlap.jaccard, overlap.mean_surface_distance_mm, overlap.hausdorff_distance_mm)
```

`OrganPipeline.run(volume, ground_truth_mask=...)` wires this in
automatically when a ground-truth mask (same shape as the *preprocessed*
volume) is supplied.

## What this repository validates, concretely

- **Lungs, heart (CT):** end-to-end against the real chest CT fixture
  (`data/volumes/CTChest.nrrd`) in `tests/test_lungs_pipeline.py` and
  `tests/test_heart_pipeline.py` — plausible volume, watertight mesh,
  expected component count.
- **Heart (ex-vivo synchrotron tomography):** the `modality="synchrotron"`
  branch (`configs/heart_synchrotron.yaml`) was developed and run
  end-to-end against a real specimen — LADAF-2021-17, 169.36 µm overview
  resolution, from the ESRF Human Organ Atlas / HiP-CT project
  (https://human-organ-atlas.esrf.fr) — producing a watertight,
  single-body mesh with a recognizable cardiac silhouette (apex, base,
  attached great-vessel stump). **That raw dataset (~150MB compressed) is
  not committed to this repository**: it exceeds GitHub's 100MB
  per-file limit for a normal commit, and vendoring third-party
  synchrotron-facility data into a general-purpose reconstruction repo
  works against the project's own minimalism (see AUDIT.md). The
  automated test suite instead covers this branch
  (`tests/test_heart_pipeline.py::test_heart_pipeline_synchrotron_end_to_end`,
  `tests/test_io.py`) against a small synthetic slice-sequence phantom
  that reproduces the same intensity relationships (background
  ~24000–26000, tissue ~27000+, cylindrical sample-holder tube) — pipeline
  mechanics, not a substitute for the real-data result already obtained.
  To reproduce it: download a specimen from the Human Organ Atlas
  (registration/terms of use apply on their end), then
  `python main.py --input path/to/slices_or.zip --organ heart --modality synchrotron --spacing SX SY SZ`.
- **Liver, kidneys:** end-to-end against synthetic phantoms
  (`tests/conftest.py`, `tests/test_liver_pipeline.py`,
  `tests/test_kidneys_pipeline.py`) — this repository does not ship an
  abdominal CT or synchrotron fixture for either organ, so these tests
  check pipeline *mechanics* (segmentation converges to a watertight mesh,
  recovers most of a known synthetic volume) rather than clinical accuracy
  on real anatomy.
- **Geometry correctness:** `tests/test_mesh_metrics.py` checks computed
  volume, surface area, centroid, and bounding box against closed-form
  sphere geometry — this is what would fail if the coordinate transform
  in `core/mesh.py` had a units or axis-order bug.

If you have expert-labeled CT/MRI data for any of these organs, running
`compute_overlap_metrics` against it (and, ideally, adding it as a
fixture the way `CTChest.nrrd` is used here) is the natural next step to
turn the plausibility-range validation into a real accuracy measurement.
