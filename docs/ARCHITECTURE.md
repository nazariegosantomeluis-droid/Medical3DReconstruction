# Arquitectura

## Objetivos de diseño, en orden de prioridad

1. **Corrección científica** — las transformaciones de coordenadas, las
   métricas de malla y la lógica de validación son correctas y se prueban
   contra geometría de forma cerrada, no solo "se ejecuta sin fallar".
2. **Reproducibilidad** — cada parámetro que afecta a un resultado de
   segmentación vive en una configuración YAML versionada, no en una
   constante fija enterrada dentro de una función.
3. **Modularidad** — cada pipeline de órgano es una unidad autocontenida
   que implementa la misma pequeña interfaz (`OrganPipeline`), de modo que
   añadir un sexto órgano significa añadir un sexto paquete, no tocar los
   otros cinco (así se añadió el cerebro como quinto órgano).
4. **Mantenibilidad** — las operaciones genéricas de geometría/imagen se
   factorizan una sola vez en `core/`; las decisiones anatómicas
   específicas de cada órgano no.
5. **Validación** — cada ejecución del pipeline termina en un reporte de
   validación, no solo en una malla. Una malla sin una verificación de
   sensatez de volumen/estanqueidad no es un entregable, es un pasivo.

## El contrato de `OrganPipeline`

Cada órgano implementa exactamente tres métodos:

```python
class OrganPipeline(ABC):
    def preprocess(self, volume: Volume) -> Volume: ...
    def segment(self, volume: Volume) -> np.ndarray: ...
    def postprocess(self, mask: np.ndarray, volume: Volume) -> np.ndarray: ...
```

`OrganPipeline.run()` (en `organs/base.py`) luego llama, en orden:
`preprocess → segment → postprocess → generate_mesh → optimize_mesh →
validate`, y devuelve un `PipelineResult` que lleva juntos la máscara, la
malla, las métricas y el reporte de validación. Los últimos tres pasos
(generación de malla, optimización de malla, validación) tienen valores
predeterminados compartidos y sensatos construidos a partir de `core/`,
pero cualquier órgano puede sobrescribirlos si su geometría lo justifica
con ajustes de malla distintos — que es exactamente lo que ya
parametriza la configuración YAML de cada órgano (`mesh_smoothing_sigma`,
`mesh_taubin_iterations`, `mesh_decimate_target_fraction`).

## Por qué parte del código se comparte y parte no

La especificación exige que cada órgano tenga un **pipeline independiente**
sin **algoritmo de segmentación compartido**. Esto se implementa así:

- **Nunca compartido:** `segment()` para cada órgano es un módulo distinto
  con lógica distinta — el umbralizado pulmonar, el crecimiento de
  regiones hepático y los level sets de corazón/riñón no se llaman entre
  sí ni a un despachador ("segment(organ_name)") común. El corazón y los
  riñones usan ambos un level set de contorno activo geodésico porque
  ambos necesitan conciencia de bordes (la misma conclusión a la que
  llegó el trabajo previo del proyecto), pero son dos implementaciones
  separadas (`organs/heart/segmentation.py` y
  `organs/kidneys/segmentation.py`), cada una con su propia ROI, búsqueda
  de semilla y ajuste — no una función parametrizada por órgano.
- **Compartido, deliberadamente:** marching cubes (`core/mesh.py`), el
  suavizado/decimación/reparación de malla (`core/mesh_ops.py`), la
  exportación STL/OBJ/PLY (`core/exporters.py`) y la validación de
  Dice/plausibilidad (`core/validation.py`) son geometría e E/S genéricas —
  toman una máscara o una malla como entrada y no saben nada sobre qué
  órgano la produjo. Reimplementar marching cubes cinco veces no haría al
  código más "independiente", solo serían cinco copias del mismo error
  esperando divergir. De igual forma, `core/preprocessing_utils.py`
  contiene primitivas de nivel biblioteca (resample, denoise, recorte de
  ROI, componentes conexas) que el `preprocessing.py` de cada órgano
  compone de forma diferente — la composición y las fracciones de ROI
  anatómicas son específicas de cada órgano; la llamada subyacente a
  numpy/SimpleITK no lo es.

## Corrección de coordenadas

Esta es la parte del código con más probabilidad de producir
silenciosamente un resultado incorrecto pero de apariencia plausible, así
que está centralizada en un solo lugar:
`Volume.index_to_world()` (`core/volume.py`) y el manejo de ejes de
marching cubes en `core/mesh.py`. Ver los docstrings de esos módulos para
la convención exacta (orden de array `(z, y, x)` de SimpleITK/NumPy,
fórmula de espacio físico de ITK `world = origin + D @ (spacing * index)`,
y por qué la dirección (winding) de las caras se repara siempre de forma
incondicional mediante `trimesh.repair.fix_normals` en lugar de confiar en
la salida de marching cubes — reordenar `(z, y, x)` a `(x, y, z)` es en sí
mismo una reflexión, así que una malla derivada de forma ingenua tendría
normales hacia adentro independientemente de los cosenos de dirección
propios de la adquisición).

## Limitaciones conocidas

- Los priors de ROI para corazón/hígado/riñones (`roi_x_fraction`, etc. en
  sus configuraciones) son heurísticas de espacio de coordenadas que
  asumen una TC axial estándar en orientación LPS con la anatomía
  relevante dentro del campo de visión — no un registro con atlas.
  Necesitarán reajustarse para un protocolo de escaneo distinto (p. ej.
  una TC solo de tórax no tiene hígado ni riñones que encontrar).
- Los pipelines de hígado y riñón se validan en este repositorio contra
  fantomas sintéticos, no contra TC abdominal real (ver
  `docs/VALIDATION.md`).
- Los level sets de corazón y riñón se inicializan (seed) a partir de una
  heurística de intensidad tosca, no de un detector entrenado — una
  anatomía inusual (p. ej. post-quirúrgica, congénita) puede necesitar
  ajuste del radio de semilla o de la ROI.
</content>
