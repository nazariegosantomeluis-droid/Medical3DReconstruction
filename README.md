# Medical3DReconstruction

Reconstruye una malla de superficie 3D validada de un órgano — **pulmones,
corazón, hígado, riñones o cerebro** — a partir de un volumen de TC/RM o de
tomografía sincrotrón ex-vivo, usando un pipeline de segmentación clásico
(no basado en aprendizaje automático) e independiente para cada órgano.

```
Volumen TC/RM  →  segmentación específica del órgano  →  malla 3D  →  métricas + validación  →  STL / OBJ / PLY
```

## Alcance

Este proyecto hace exactamente una cosa: convertir un único volumen de
TC/RM (o de tomografía sincrotrón ex-vivo) en una malla imprimible en 3D y
métricamente validada de uno de cinco órganos. Deliberadamente **no** es:

- un visor PACS o DICOM,
- una plataforma de segmentación por IA/aprendizaje profundo,
- una suite de procesamiento de imágenes de propósito general al estilo 3D Slicer,
- un atlas multiórgano o un framework de registro (registration).

No existe una función genérica y compartida "segment(organ)". Pulmones,
corazón, hígado, riñones y cerebro tienen cinco pipelines independientes
porque fallan bajo un enfoque único para todos — ver
[`docs/ORGAN_PIPELINES.md`](docs/ORGAN_PIPELINES.md) para entender por qué
cada órgano necesita el algoritmo que usa. El cerebro es un caso especial:
solo se admite a partir de tomografía sincrotrón ex-vivo (ver
[`docs/ORGANOS.md`](docs/ORGANOS.md) y la sección de tomografía sincrotrón
más abajo) — este proyecto no incluye un pipeline clínico de TC/RM para
cerebro.

## Inicio rápido

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python main.py --input data/volumes/CTChest.nrrd --organ lungs
```

Esto carga el volumen, ejecuta el pipeline pulmonar (preprocess → segment →
postprocess → mesh → optimize → validate), imprime las métricas y el reporte
de validación, exporta `outputs/lungs.{stl,obj,ply}`, y renderiza una vista
previa en `outputs/lungs_preview.png`.

Pasa `--visualize html` en su lugar para obtener un visor interactivo
autocontenido (`outputs/lungs_viewer.html`) — una vista 3D rotable/con zoom
de la malla más un explorador de cortes de TC con ventana (windowing) sobre
el volumen original, todo en un único archivo que puedes abrir en cualquier
navegador sin servidor ni instalación. Ver
[notas de visualización 3D](#notas-de-visualización-3d) más abajo.

```bash
python main.py --input <volume-or-dicom-dir> --organ {lungs,heart,liver,kidneys,brain} \
    [--modality {CT,MRI,synchrotron}] \
    [--spacing SX SY SZ] \
    [--config configs/<organ>.yaml] \
    [--output-dir outputs] \
    [--formats stl obj ply] \
    [--visualize {interactive,screenshot,html,none}] \
    [--metrics-json outputs/<organ>_metrics.json]
```

`--input` acepta un único archivo de volumen (`.nrrd`, `.nii`, `.nii.gz`,
`.mha`, `.mhd`) o un directorio que contenga una serie DICOM. Con
`--modality synchrotron` (tomografía ex-vivo por contraste de fase, p. ej.
el ESRF Human Organ Atlas / HiP-CT), `--input` toma en su lugar un
directorio o `.zip` de imágenes de corte 2D (JP2/TIFF/PNG), y `--spacing` es
obligatorio — estos archivos no llevan metadatos fiables de espaciado físico
de los que leerlo. Ver
[`docs/ORGAN_PIPELINES.md`](docs/ORGAN_PIPELINES.md#corazón--variante-de-tomografía-por-síncrotrón-ex-vivo).

## Qué se calcula

Para la malla reconstruida:

- **Volumen** (mm³ y mL) — a partir de la geometría con signo de la malla,
  no de un conteo de voxeles, de modo que refleja lo que realmente se
  exporta.
- **Área de superficie** (mm²)
- **Centroide** (mm, espacio físico del paciente)
- **Caja delimitadora (bounding box)** (mm, esquinas mínima/máxima)
- **Número de vértices** y **número de triángulos**

Además de un reporte de validación: estanqueidad/consistencia de dirección
(winding) de la malla, una verificación de plausibilidad de volumen
anatómico informada por la literatura, y (cuando hay disponible una máscara
de referencia/ground truth) Dice, Jaccard y distancia de superficie.

## Arquitectura

```
main.py                      CLI: load → select organ → run → report → export → visualize
src/medical3d/
  io/                         Carga de volúmenes (serie DICOM, NRRD/NIfTI/MHA) + validación
  core/
    volume.py                 Volume: array + spacing/origin/direction, matemática de espacio físico
    config.py                 Configuración YAML por órgano
    preprocessing_utils.py     Operaciones de imagen genéricas compartidas entre órganos (resample, denoise, ROI crop)
    mesh.py                    Marching cubes, métricas de malla
    mesh_ops.py                Suavizado, decimación, reparación, evaluación de calidad
    validation.py               Dice/Jaccard/distancia de superficie, rangos de plausibilidad
    exporters.py                Exportación STL/OBJ/PLY
    visualization.py            Renderizado 3D (PyVista, con reserva a Matplotlib)
    html_viewer.py               Exportación HTML interactiva autocontenida (vista de malla WebGL + explorador de cortes de TC)
  organs/
    base.py                    OrganPipeline ABC: preprocess → segment → postprocess → mesh → optimize → validate
    lungs/                      umbral (threshold) + componentes conexas
    heart/                      level set de contorno activo geodésico con conciencia de bordes (CT) / umbral (síncrotrón ex-vivo)
    liver/                      crecimiento de regiones por conectividad de confianza con semilla (CT) / umbral (síncrotrón ex-vivo)
    kidneys/                    level set de contorno activo geodésico bilateral con conciencia de bordes (CT) / umbral (síncrotrón ex-vivo)
    brain/                      umbral + componente conexa más grande (solo síncrotrón ex-vivo, sin pipeline clínico)
configs/<organ>.yaml           Parámetros por órgano (umbrales, priors de ROI, ajustes de malla)
tests/                         Pruebas de pipeline con TC real y fantomas sintéticos, pruebas unitarias de geometría
docs/                          Justificación de la arquitectura, descripciones del algoritmo por órgano, metodología de validación
```

El código de geometría genérico (marching cubes, suavizado/decimación de
malla, exportación, verificaciones de plausibilidad) se comparte a través de
`core/`, porque es matemática de nivel biblioteca sin decisiones específicas
de órgano. **La segmentación no se comparte** — el `segmentation.py` de cada
órgano está implementado y ajustado de forma independiente; ver
[`AUDIT.md`](AUDIT.md) y [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) para
el razonamiento.

## Por qué cada órgano usa el algoritmo que usa

| Órgano | Enfoque | Por qué |
|---|---|---|
| Pulmones | Umbral de HU con máscara corporal + componentes conexas | El pulmón aireado es >500 HU, separado de todo el tejido circundante — un umbral global basta una vez excluido el aire de fondo mediante una máscara corporal. |
| Corazón (TC) | Level set de contorno activo geodésico con conciencia de bordes | La HU del miocardio/pool sanguíneo se superpone con los grandes vasos, la grasa pericárdica y el diafragma — un umbral se filtra (leak); el level set se detiene en los gradientes de imagen (bordes), no en la intensidad. |
| Corazón (síncrotrón ex-vivo) | Umbral + componente conexa más grande | La tomografía por contraste de fase da un contraste de tejido blando mucho mayor que la TC clínica — una vez excluido geométricamente el tubo portamuestras, el tejido se separa limpiamente solo por intensidad. |
| Hígado (TC) | Crecimiento de regiones por conectividad de confianza con semilla | El parénquima hepático es homogéneo pero no único en intensidad (se superpone con bazo/riñón/músculo) — el crecimiento de regiones desde una semilla en el cuadrante superior derecho, adaptándose a las estadísticas locales, contiene la fuga. |
| Hígado (síncrotrón ex-vivo) | Umbral + componente conexa más grande | El espécimen real llena el cuadro sin margen de tubo portamuestras visible — solo hace falta umbral + downsampling, sin recorte geométrico. |
| Riñones (TC) | Level set de contorno activo geodésico bilateral con conciencia de bordes | Mismo problema de superposición que el corazón (parénquima renal vs. músculo psoas), ejecutado de forma independiente desde dos semillas para los dos riñones. |
| Riñones (síncrotrón ex-vivo) | Umbral + componente conexa más grande | El archivo K292 es un único riñón excisado, no un par bilateral — no hace falta la lógica de doble semilla de la variante clínica. |
| Cerebro (síncrotrón ex-vivo, único modo admitido) | Umbral + componente conexa más grande | Un escaneo "órgano completo" llena casi todo el tubo con tejido — solo se excluye el tubo geométricamente (igual que el corazón), sin medio de montaje independiente que separar por intensidad. No existe pipeline clínico de TC/RM para cerebro en este proyecto. |

La justificación completa, los parámetros y las limitaciones conocidas de
cada órgano están en
[`docs/ORGAN_PIPELINES.md`](docs/ORGAN_PIPELINES.md).

## Validación

- **Pulmones** se valida de extremo a extremo contra una TC de tórax real
  (`data/volumes/CTChest.nrrd`, incluida en este repositorio) — volumen
  anatómico plausible, malla estanca (watertight), cuerpo único conectado.
- **Corazón, hígado, riñones y cerebro** (modo síncrotrón ex-vivo) se han
  ejecutado contra especímenes reales del ESRF Human Organ Atlas / HiP-CT
  (no incluidos en este repositorio por su tamaño — decenas a cientos de
  MB por archivo; ver [`docs/ORGAN_PIPELINES.md`](docs/ORGAN_PIPELINES.md)
  para cómo obtenerlos) — producen mallas estancas de un único cuerpo
  conectado. Sus volúmenes reconstruidos con frecuencia caen **fuera** del
  rango de plausibilidad para un paciente vivo (ver
  `PLAUSIBLE_VOLUME_RANGES_ML` en `core/validation.py`): esto es esperado,
  no un fallo del pipeline — un espécimen ex-vivo fijado/preservado no
  tiene el mismo volumen que el órgano en un paciente vivo. Las variantes
  clínicas (TC) de corazón, hígado y riñones se validan contra fantomas
  sintéticos (ver `tests/conftest.py`), porque este repositorio no incluye
  un fixture de TC abdominal/cardíaca. Las pruebas con fantomas confirman
  la *mecánica* del pipeline (la segmentación converge, la malla es
  estanca, se recupera la mayor parte del volumen sintético conocido) — no
  sustituyen la validación contra datos clínicos etiquetados por expertos.
- Trabajo previo de este proyecto midió Dice 0.918 (hígado) y Dice 0.862
  (pulmón) contra datos etiquetados por expertos; esos son los puntos de
  referencia que el *enfoque* de segmentación de cada órgano fue elegido
  para reproducir, no una afirmación sobre este código exacto sin
  volver a ejecutarlo contra esos datos etiquetados. Ver
  [`docs/VALIDATION.md`](docs/VALIDATION.md) para saber cómo validar contra
  tus propias máscaras de referencia (ground truth).

## Pruebas

```bash
pytest
```

Corrección de la geometría de malla contra volumen/área de superficie/
centroide de una esfera en forma cerrada, operaciones de malla (suavizado,
decimación, reparación), ciclos completos de exportación STL/OBJ/PLY,
lógica de validación de Dice/Jaccard/plausibilidad, E/S de volúmenes
(incluida la carga de pilas de cortes síncrotrón), y los cinco pipelines de
órgano de extremo a extremo — pulmones contra el fixture de TC real;
corazón, hígado, riñones y cerebro contra fantomas sintéticos síncrotrón
(mismas relaciones de intensidad que los datos reales, ver
`tests/conftest.py`), y corazón, hígado y riñones además contra fantomas
sintéticos de su variante clínica (TC).

## Notas de visualización 3D

El renderizado usa PyVista/VTK por defecto. Las coordenadas del mundo
siguen la convención ITK/DICOM (X=Izquierda, Y=Posterior, Z=Superior para
una adquisición alineada con los ejes), que ya es un sistema de mano
derecha con el eje Z hacia arriba — el view-up de la cámara está fijado a
`(0, 0, 1)` para que los órganos nunca se rendericen de lado, y
`--visualize interactive` abre una ventana interactiva real. Las normales
de la malla siempre apuntan hacia afuera (`trimesh.repair.fix_normals` se
ejecuta incondicionalmente después de marching cubes), que es lo que hace
que un órgano reconstruido se renderice correctamente iluminado en lugar de
verse mate-negro/"al revés".

En entornos sin interfaz gráfica (headless) sin contexto GPU/EGL/OSMesa,
`--visualize screenshot` recurre automáticamente a una vista previa
renderizada con Matplotlib (el mecanismo de reserva primero intenta el
renderizado arriesgado con PyVista en un subproceso aislado, ya que un
controlador de renderizado fuera de pantalla ausente puede provocar un
segfault de VTK a nivel de C).

`--visualize html` (`core/html_viewer.py`) evita por completo el problema
de GPU fuera de pantalla: exporta un único archivo HTML con un renderizador
WebGL escrito a mano y sin dependencias (sin PyVista/VTK, sin scripts de
CDN) más un explorador de cortes de TC con ventana (arrastra el control
deslizante de corte, ajusta el nivel/ancho de ventana, o usa los presets de
Pulmón/Tejido blando/Hueso) sobre el volumen original — ábrelo en cualquier
navegador, en cualquier máquina, sin nada instalado. Complementa, no
reemplaza, la exportación de malla y las métricas: el archivo es un visor,
sin edición, anotación ni gestión de múltiples estudios, por lo que no
cambia el alcance de este proyecto respecto a la reconstrucción de un solo
órgano (ver [Alcance](#alcance)).

## Licencia

MIT — ver [`LICENSE`](LICENSE).
</content>
