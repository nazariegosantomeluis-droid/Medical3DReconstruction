# Organ pipelines

Each section covers the algorithm, why it was chosen over the
alternatives, the config parameters that control it, and known failure
modes. Config files live in `configs/<organ>.yaml`.

## Lungs

**Algorithm:** per-slice body silhouette → HU threshold → connected-component
selection (classical approach after Hu, Hoffman & Reinhardt, 2001).

1. **Preprocessing** (`organs/lungs/preprocessing.py`): Gaussian denoise,
   optional resample to isotropic spacing.
2. **Segmentation** (`organs/lungs/segmentation.py`):
   - Build a per-slice body silhouette: on each axial slice, take the
     largest connected region above `body_threshold_hu` (skin/chest wall)
     and fill it in. This is necessary, not cosmetic: the respiratory
     tract is one continuous air column from the airway opening to the
     alveoli, so a naive "remove whatever touches the 3D volume border"
     pass leaks straight through the trachea and merges the lungs with
     the scanner's background air into one component. Building the body
     mask per-slice and intersecting it with the air threshold prevents
     that regardless of how the airway connects to outside air.
   - Threshold at `air_threshold_hu` (default −320 HU) inside the body
     mask.
   - Keep the `num_components` (default 2) largest air pockets — the
     trachea/main bronchi form a much smaller connected volume than
     either lung, so size ranking (not explicit airway tracing) separates
     them.
3. **Postprocessing** (`organs/lungs/postprocessing.py`): fill holes
   (recovers vessels/nodules inside the lung field, which are soft-tissue
   density and would otherwise be excluded by the threshold), morphological
   closing (smooths the pleural surface, reincorporates juxtapleural
   structures), then re-apply the largest-component filter since closing
   can introduce small stray islands.

**Why not a learned model:** lung/soft-tissue HU separation (>500 HU) is
large enough that classical thresholding is both simpler and more
auditable than a network, with no accuracy tradeoff for this population.

**Known failure modes:** severe emphysema or pneumothorax changes the
expected component count/shape; pleural effusion (fluid, not air) is not
segmented by an air threshold and would need a separate approach.

## Heart

**Algorithm:** boundary-aware geodesic active contour (GAC) level set.

1. **Preprocessing** (`organs/heart/preprocessing.py`): crop to a
   mediastinal ROI (`roi_x/y/z_fraction`, a coordinate-space heuristic
   standing in for atlas registration), resample to isotropic spacing,
   denoise.
2. **Segmentation** (`organs/heart/segmentation.py`):
   - Gradient magnitude of the ROI (`gradient_sigma_mm`).
   - Sigmoid-map the gradient to a speed image in `[0, 1]`: near 1 in
     homogeneous interior regions, near 0 at strong edges.
   - Auto-seed at the centroid of soft-tissue-range voxels
     (`seed_hu_range`, default 0–100 HU, unenhanced myocardium/blood
     pool) within the ROI.
   - Initialize the level set as a signed distance function of a small
     sphere (`initial_sphere_radius_mm`) around the seed.
   - Evolve with `sitk.GeodesicActiveContourLevelSetImageFilter`
     (`propagation_scaling`, `curvature_scaling`, `advection_scaling`,
     `max_iterations`, `max_rms_error`); threshold the result at 0.
3. **Postprocessing** (`organs/heart/postprocessing.py`): keep the single
   largest component, fill holes, morphological closing.

**Why not a threshold:** myocardium/blood pool HU (unenhanced, roughly
0–100) overlaps the great vessels, pericardial fat boundary, and
diaphragm. A pure threshold leaks into the aorta/vena cava and beyond —
exactly the failure mode the project's prior work flagged as needing
boundary-aware segmentation. The level set instead stops at image
*edges* (high gradient magnitude → near-zero speed), which is where the
true anatomical boundary actually is regardless of the HU on either side
of it.

**Known failure modes:** this segments the whole cardiac silhouette
(chambers + myocardium + attached great vessel stumps), not
chamber-by-chamber; a very weak endocardial/epicardial gradient (thin,
low-dose, or motion-blurred acquisitions) can under- or over-shoot the
true boundary and needs `advection_scaling`/`curvature_scaling` retuning.

### Heart — ex-vivo synchrotron tomography variant

`configs/heart_synchrotron.yaml`, `modality="synchrotron"` in
`organs/heart/{preprocessing,segmentation}.py`.

Clinical non-contrast CT is not the only real data this project has been
validated against. The ESRF Human Organ Atlas / HiP-CT project
(https://human-organ-atlas.esrf.fr) publishes ex-vivo phase-contrast
synchrotron tomography of donated organs — a specimen (LADAF-2021-17
heart, 169.36 µm overview resolution, 870×870×1020 voxels) was used to
validate this branch. It is a genuinely different acquisition, not just a
higher-resolution CT, so it gets its own algorithm rather than a config
tweak on the CT one:

1. **Preprocessing**: the specimen sits in a cylindrical sample-holder
   tube. The tube wall is *denser* than the tissue of interest, so no
   intensity threshold could separate "tissue" from "tube" — instead the
   tube is excluded geometrically, cropping every slice to a circle
   (`tube_radius_fraction`) sized to its inner wall.
2. **Segmentation**: a plain intensity threshold
   (`tissue_intensity_threshold`) plus morphological opening (denoise)
   plus largest-connected-component. Ex-vivo phase-contrast tomography has
   dramatically better soft-tissue contrast than clinical CT — background
   mounting medium and tissue are already well separated once the tube is
   gone — so the boundary-aware level set the CT branch needs would be
   solving a problem this modality doesn't have.
3. **Postprocessing**: same closing + hole-filling as the CT branch, just
   with a much smaller physical radius (`morphological_closing_radius_mm:
   0.35`) to match ~9x finer voxels.
4. **Mesh repair**: real, noisy, high-resolution data produces a
   high-genus surface (many small topological tunnels from threshold
   noise) that `trimesh.repair.fill_holes` alone can't always close.
   `core/mesh_ops.py::repair_mesh` falls back to
   [pymeshfix](https://github.com/pyvista/pymeshfix) (Attene, 2010) when
   the trimesh repair doesn't achieve watertightness — this is what
   actually got the LADAF-2021-17 reconstruction to a valid closed mesh.

**Loading this data:** it's distributed as a directory or `.zip` of 2D
slice images (JP2/TIFF/PNG), not DICOM/NIfTI, and carries no reliable
spacing metadata in the files themselves:

```bash
python main.py --input path/to/slices_or.zip --organ heart \
    --modality synchrotron --spacing 0.16936 0.16936 0.16936
```

The raw dataset (~150MB compressed) is not committed to this repository —
see docs/VALIDATION.md for why and how to reproduce this yourself.

**Known failure modes:** `tissue_intensity_threshold` and
`tube_radius_fraction` are calibrated against this specific specimen and
scanner settings (native 16-bit intensity, not a portable physical unit
like Hounsfield units) — a different specimen or acquisition will need a
slice-histogram check before reusing these defaults; the reconstructed
volume for a fixed/preserved ex-vivo specimen is not expected to fall in
the living-patient plausibility range in `core/validation.py` (tissue
shrinks under fixation), so a "not plausible" flag there is expected, not
a bug.

## Liver

**Algorithm:** seeded confidence-connected region growing.

1. **Preprocessing** (`organs/liver/preprocessing.py`): crop to a
   right-upper-quadrant ROI, resample, denoise.
2. **Segmentation** (`organs/liver/segmentation.py`): auto-seed at the
   centroid of voxels in `seed_hu_range` (default 20–70 HU) within the
   ROI, then grow with `sitk.ConfidenceConnectedImageFilter`
   (`confidence_multiplier`, `confidence_iterations`,
   `confidence_initial_neighborhood_radius`) — at each iteration, the
   region's current mean/standard deviation is re-estimated and neighbors
   within `multiplier` standard deviations are added.
3. **Postprocessing** (`organs/liver/postprocessing.py`): largest
   component, fill holes, morphological closing.

**Why region growing, not a threshold:** liver parenchyma is fairly
homogeneous but not intensity-*unique* — it overlaps spleen, kidney, and
muscle HU. A global threshold over- or under-segments depending on what
else is in the abdomen at that HU. Region growing from a point known
(via the ROI prior) to be inside the liver, adapting to local statistics
rather than a fixed band, is what reached Dice 0.918 in prior project
work referenced by this project's design notes.

**Known failure modes:** the confidence-connected filter can leak across
a thin, low-contrast boundary into the diaphragm or a directly
adjacent organ if the ROI seed lands too close to that boundary;
cirrhotic or highly heterogeneous livers (contrast enhancement, lesions)
violate the "roughly homogeneous parenchyma" assumption region growing
relies on.

## Kidneys

**Algorithm:** bilateral boundary-aware GAC level set (same class of
algorithm as the heart, independently implemented — see
`docs/ARCHITECTURE.md` for why sharing the *type* of technique is not the
same as sharing a segmentation routine).

1. **Preprocessing** (`organs/kidneys/preprocessing.py`): crop to a
   posterior-abdomen ROI spanning both flanks.
2. **Segmentation** (`organs/kidneys/segmentation.py`): compute the
   gradient/speed image once for the shared ROI; find two seeds
   independently (centroid of `seed_hu_range` voxels in the left half and
   right half of the ROI); evolve two independent level sets from those
   seeds against the same speed image; union the results.
3. **Postprocessing** (`organs/kidneys/postprocessing.py`): keep the two
   largest components (left + right kidney), fill holes, morphological
   closing.

**Why not a threshold:** unenhanced renal parenchyma HU (~30–60) overlaps
the psoas muscle and adjacent organs — the same class of problem as the
heart, hence the same class of solution.

**Known failure modes:** a horseshoe kidney or unilateral nephrectomy
breaks the "exactly two components" assumption in postprocessing;
significant hydronephrosis (fluid-filled collecting system) changes the
expected internal HU homogeneity the level set's speed function assumes.
