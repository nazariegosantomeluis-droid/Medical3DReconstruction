# Metodología de validación

Cada ejecución del pipeline produce un `ValidationReport`
(`core/validation.py`), que combina tres verificaciones independientes:

## 1. Calidad de la malla

`core/mesh_ops.py::assess_mesh_quality` reporta:

- `is_watertight` — cada arista compartida por exactamente dos caras. Una
  malla no estanca (non-watertight) tiene un volumen encerrado mal
  definido y puede no cortarse/imprimirse en 3D correctamente.
- `is_winding_consistent` — las normales de las caras concuerdan en
  qué es interior y qué es exterior.
- `euler_number`, `num_bodies` — señales de sensatez para topología
  inesperada (una malla pulmonar con 6 cuerpos desconectados
  probablemente tiene ruido de segmentación que sobrevivió al
  postprocesamiento).

`ValidationReport.passed` requiere `is_watertight` y un volumen plausible
(ver abajo); **no** requiere mallas de un solo cuerpo, ya que los pulmones
y los riñones son legítimamente bilaterales.

## 2. Plausibilidad anatómica

`PLAUSIBLE_VOLUME_RANGES_ML` en `core/validation.py` contiene rangos de
referencia amplios para adultos, informados por la literatura:

| Órgano | Rango (mL) |
|---|---|
| Pulmones | 2000–7000 |
| Corazón | 300–900 |
| Hígado | 1000–2500 |
| Riñones (ambos) | 200–450 |
| Cerebro | 1000–1600 |

Estos rangos abarcan la variación fisiológica normal (no solo el ruido de
medición) — el objetivo es detectar fallos graves de segmentación (fuga
hacia una estructura vecina, capturar solo un fragmento), no calificar la
precisión. Un resultado fuera de este rango es una **advertencia para
investigar**, no una prueba de que la segmentación esté mal (la anatomía
real varía, especialmente en los extremos del tamaño corporal) — **con una
excepción documentada**: las reconstrucciones en modalidad síncrotrón
ex-vivo (corazón, hígado, riñones, cerebro) representan especímenes
fijados/excisados, no pacientes vivos, así que caer fuera de estos rangos
—calibrados para TC/RM clínica en vivo— es un resultado esperado para esa
modalidad, no una señal de fallo. Ver `docs/ORGAN_PIPELINES.md` y
`docs/ORGANOS.md` para el detalle por órgano.

## 3. Superposición contra la referencia (ground truth) (opcional)

`compute_overlap_metrics(prediction, ground_truth, spacing)` calcula:

- **Coeficiente de Dice** e **índice de Jaccard** (superposición de
  voxeles).
- **Distancia de superficie media y de Hausdorff** (mm), a partir de los
  voxeles de frontera de cada máscara mediante una consulta de vecino más
  cercano con KD-tree en espacio físico.

Así es como se midieron originalmente los puntajes de Dice referenciados
en las notas de diseño de este proyecto — hígado 0.918, pulmón 0.862 — y
así es como deberías validar este código contra tus propios datos
etiquetados por expertos:

```python
from medical3d.core.validation import compute_overlap_metrics

overlap = compute_overlap_metrics(predicted_mask, ground_truth_mask, spacing=volume.spacing)
print(overlap.dice, overlap.jaccard, overlap.mean_surface_distance_mm, overlap.hausdorff_distance_mm)
```

`OrganPipeline.run(volume, ground_truth_mask=...)` conecta esto
automáticamente cuando se proporciona una máscara de referencia (con la
misma forma que el volumen *preprocesado*).

## Qué valida este repositorio, concretamente

- **Pulmones, corazón (TC):** de extremo a extremo contra el fixture de TC
  de tórax real (`data/volumes/CTChest.nrrd`) en
  `tests/test_lungs_pipeline.py` y `tests/test_heart_pipeline.py` —
  volumen plausible, malla estanca, número de componentes esperado.
- **Corazón (tomografía por síncrotrón ex-vivo):** la rama
  `modality="synchrotron"` (`configs/heart_synchrotron.yaml`) se
  desarrolló y ejecutó de extremo a extremo contra un espécimen real —
  LADAF-2021-17, resolución de visión general de 169.36 µm, del proyecto
  ESRF Human Organ Atlas / HiP-CT
  (https://human-organ-atlas.esrf.fr) — produciendo una malla estanca de
  un solo cuerpo con una silueta cardíaca reconocible (ápex, base, muñón
  de gran vaso adherido). **Ese conjunto de datos crudo (~150MB
  comprimido) no se incluye en este repositorio**: excede el límite de
  100MB por archivo de GitHub para un commit normal, y vendorizar datos de
  una instalación de síncrotrón de terceros en un repositorio de
  reconstrucción de propósito general va en contra del propio minimalismo
  del proyecto (ver AUDIT.md). La batería de pruebas automatizadas cubre
  en cambio esta rama
  (`tests/test_heart_pipeline.py::test_heart_pipeline_synchrotron_end_to_end`,
  `tests/test_io.py`) contra un pequeño fantoma sintético de secuencia de
  cortes que reproduce las mismas relaciones de intensidad (fondo
  ~24000–26000, tejido ~27000+, tubo portamuestras cilíndrico) —
  mecánica del pipeline, no un sustituto del resultado ya obtenido con
  datos reales. Para reproducirlo: descarga un espécimen del Human Organ
  Atlas (aplican registro/términos de uso de su parte), luego
  `python main.py --input path/to/slices_or.zip --organ heart --modality synchrotron --spacing SX SY SZ`.
- **Hígado, riñones (TC):** de extremo a extremo contra fantomas sintéticos
  (`tests/conftest.py`, `tests/test_liver_pipeline.py`,
  `tests/test_kidneys_pipeline.py`) — este repositorio no incluye un
  fixture de TC abdominal para ninguno de los dos órganos, así que estas
  pruebas verifican la *mecánica* del pipeline (la segmentación converge a
  una malla estanca, se recupera la mayor parte de un volumen sintético
  conocido) en lugar de la precisión clínica sobre anatomía real.
- **Hígado (tomografía por síncrotrón ex-vivo):** la rama
  `modality="synchrotron"` (`configs/liver_synchrotron.yaml`) se ejecutó
  de extremo a extremo contra un espécimen real — hígado LADAF-2021-17,
  resolución de visión general de 180.48 µm (el volumen nativo más grande
  de los cinco órganos, ~1.6 mil millones de voxeles) — produciendo una
  malla estanca de un solo cuerpo. Este archivo es tan grande que decodificarlo
  a resolución nativa antes de cualquier downsampling agotaba la memoria
  antes de que el preprocesamiento llegara a ejecutarse — ver
  `load_stride` en `io/volume_loader.py`, que reduce la resolución
  *mientras decodifica*, no después. Igual que con el corazón, este
  conjunto de datos crudo (~320MB comprimido) no se incluye en el
  repositorio; la batería de pruebas cubre esta rama
  (`tests/test_liver_pipeline.py::test_liver_pipeline_synchrotron_end_to_end`)
  contra un fantoma sintético con las mismas relaciones de intensidad
  (fondo ~17200–18200, tejido ~19100–21000).
- **Riñones (tomografía por síncrotrón ex-vivo):** la rama
  `modality="synchrotron"` (`configs/kidneys_synchrotron.yaml`) se ejecutó
  de extremo a extremo contra un espécimen real — riñón K292, resolución
  de visión general de 163.52 µm — un único riñón excisado, no un par
  bilateral, así que `num_components: 1` reemplaza la lógica de dos
  componentes de la variante de TC. Igual que arriba, este conjunto de
  datos crudo (~67MB comprimido) no se incluye en el repositorio; la
  batería de pruebas cubre esta rama
  (`tests/test_kidneys_pipeline.py::test_kidneys_pipeline_synchrotron_end_to_end`)
  contra un fantoma sintético (fondo ~42600–43600, tejido ~43600–45600).
- **Cerebro (tomografía por síncrotrón ex-vivo, único modo admitido):** la
  rama `modality="synchrotron"` (`configs/brain_synchrotron.yaml`) se
  ejecutó de extremo a extremo contra un espécimen real — cerebro
  LADAF-2021-17, resolución de visión general de 169.6 µm — produciendo
  una malla estanca de un solo cuerpo (~2248 mL, por encima del rango de
  plausibilidad en vivo — ver `docs/ORGANOS.md` para la interpretación).
  Igual que arriba, este conjunto de datos crudo (~125MB comprimido) no se
  incluye en el repositorio; la batería de pruebas cubre esta rama
  (`tests/test_brain_pipeline.py::test_brain_pipeline_synchrotron_end_to_end`)
  contra un fantoma sintético (tejido llenando casi todo el tubo, ~4000
  unidades nativas, sin medio de montaje separado que umbralizar).
- **Corrección geométrica:** `tests/test_mesh_metrics.py` verifica el
  volumen, el área de superficie, el centroide y la caja delimitadora
  calculados contra la geometría de una esfera en forma cerrada — esto es
  lo que fallaría si la transformación de coordenadas en `core/mesh.py`
  tuviera un error de unidades o de orden de ejes.

Si tienes datos de TC/RM etiquetados por expertos para cualquiera de estos
órganos, ejecutar `compute_overlap_metrics` contra ellos (e, idealmente,
añadirlos como un fixture de la forma en que se usa aquí `CTChest.nrrd`)
es el siguiente paso natural para convertir la validación por rango de
plausibilidad en una medición de precisión real.
</content>
