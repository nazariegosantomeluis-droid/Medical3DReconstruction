# Architecture

## Design goals, in priority order

1. **Scientific correctness** — coordinate transforms, mesh metrics, and
   validation logic are correct and tested against closed-form geometry,
   not just "runs without crashing."
2. **Reproducibility** — every parameter that affects a segmentation
   result lives in a versioned YAML config, not a hard-coded constant
   buried in a function.
3. **Modularity** — each organ pipeline is a self-contained unit
   implementing the same small interface (`OrganPipeline`), so adding a
   fifth organ means adding a fifth package, not touching the other four.
4. **Maintainability** — generic geometry/image operations are factored
   into `core/` once; organ-specific anatomical decisions are not.
5. **Validation** — every pipeline run ends in a validation report, not
   just a mesh. A mesh with no volume/watertightness sanity check is not
   a deliverable, it's a liability.

## The `OrganPipeline` contract

Every organ implements exactly three methods:

```python
class OrganPipeline(ABC):
    def preprocess(self, volume: Volume) -> Volume: ...
    def segment(self, volume: Volume) -> np.ndarray: ...
    def postprocess(self, mask: np.ndarray, volume: Volume) -> np.ndarray: ...
```

`OrganPipeline.run()` (in `organs/base.py`) then calls, in order:
`preprocess → segment → postprocess → generate_mesh → optimize_mesh →
validate`, and returns a `PipelineResult` carrying the mask, mesh,
metrics, and validation report together. The last three steps
(mesh generation, mesh optimization, validation) have sensible shared
defaults built from `core/`, but any organ can override them if its
geometry warrants different mesh settings — which is exactly what each
organ's YAML config already parameterizes (`mesh_smoothing_sigma`,
`mesh_taubin_iterations`, `mesh_decimate_target_fraction`).

## Why some code is shared and some isn't

The spec requires each organ to have an **independent pipeline** with **no
shared segmentation algorithm**. This is implemented as:

- **Not shared, ever:** `segment()` for each organ is a distinct module
  with distinct logic — lung thresholding, liver region growing, and
  heart/kidney level sets do not call into each other or into a common
  "segment(organ_name)" dispatcher. Heart and kidneys both use a geodesic
  active contour level set because both need boundary-awareness (the
  same conclusion the project's prior work reached), but they are two
  separate implementations (`organs/heart/segmentation.py` and
  `organs/kidneys/segmentation.py`), each with its own ROI, seed-finding,
  and tuning — not one function parameterized by organ.
- **Shared, deliberately:** marching cubes (`core/mesh.py`), mesh
  smoothing/decimation/repair (`core/mesh_ops.py`), STL/OBJ/PLY export
  (`core/exporters.py`), and Dice/plausibility validation
  (`core/validation.py`) are generic geometry and I/O — they take a mask
  or a mesh as input and know nothing about which organ produced it.
  Re-implementing marching cubes four times would not make the codebase
  more "independent," it would just be four copies of the same bug
  waiting to diverge. Likewise `core/preprocessing_utils.py` holds
  library-grade primitives (resample, denoise, ROI crop, connected
  components) that every organ's `preprocessing.py` composes differently
  — the composition and the anatomical ROI fractions are organ-specific;
  the underlying numpy/SimpleITK call is not.

## Coordinate correctness

This is the part of the codebase most likely to silently produce a
wrong-but-plausible-looking result, so it's centralized in one place:
`Volume.index_to_world()` (`core/volume.py`) and the marching-cubes axis
handling in `core/mesh.py`. See the module docstrings there for the exact
convention (SimpleITK/NumPy `(z, y, x)` array order, ITK physical-space
formula `world = origin + D @ (spacing * index)`, and why face winding is
unconditionally repaired via `trimesh.repair.fix_normals` rather than
trusted from marching cubes' output — reordering `(z, y, x)` to `(x, y, z)`
is itself a reflection, so a mesh derived naively would have inward
normals regardless of the acquisition's own direction cosines).

## Known limitations

- ROI priors for heart/liver/kidneys (`roi_x_fraction` etc. in their
  configs) are coordinate-space heuristics assuming a standard axial CT
  in LPS orientation with the relevant anatomy in the field of view —
  not an atlas registration. They will need retuning for a different
  scan protocol (e.g. a chest-only CT has no liver/kidneys to find).
- Liver and kidney pipelines are validated in this repo against synthetic
  phantoms, not real abdominal CT (see `docs/VALIDATION.md`).
- The heart and kidney level sets are seeded from a coarse intensity
  heuristic, not a trained detector — an unusual anatomy (e.g. post-
  surgical, congenital) may need seed-radius or ROI adjustment.
