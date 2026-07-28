# Pipelines de órgano

Cada sección cubre el algoritmo, por qué se eligió frente a las
alternativas, los parámetros de configuración que lo controlan y los modos
de fallo conocidos. Los archivos de configuración viven en
`configs/<organ>.yaml`.

## Pulmones

**Algoritmo:** silueta corporal por corte → umbral de HU → selección de
componente conexa (enfoque clásico según Hu, Hoffman & Reinhardt, 2001).

1. **Preprocesamiento** (`organs/lungs/preprocessing.py`): eliminación de
   ruido gaussiano, remuestreo opcional a espaciado isotrópico.
2. **Segmentación** (`organs/lungs/segmentation.py`):
   - Construir una silueta corporal por corte: en cada corte axial, se
     toma la región conexa más grande por encima de `body_threshold_hu`
     (piel/pared torácica) y se rellena. Esto es necesario, no cosmético:
     el tracto respiratorio es una columna de aire continua desde la
     apertura de la vía aérea hasta los alvéolos, así que una pasada
     ingenua de "eliminar lo que toque el borde del volumen 3D" se filtra
     directamente a través de la tráquea y fusiona los pulmones con el
     aire de fondo del escáner en un solo componente. Construir la máscara
     corporal corte a corte e intersectarla con el umbral de aire evita
     eso sin importar cómo se conecte la vía aérea con el aire exterior.
   - Umbralizar en `air_threshold_hu` (por defecto −320 HU) dentro de la
     máscara corporal.
   - Conservar las `num_components` (por defecto 2) bolsas de aire más
     grandes — la tráquea/bronquios principales forman un volumen conexo
     mucho más pequeño que cualquiera de los dos pulmones, así que el
     ordenamiento por tamaño (no un trazado explícito de la vía aérea) los
     separa.
3. **Postprocesamiento** (`organs/lungs/postprocessing.py`): relleno de
   huecos (recupera vasos/nódulos dentro del campo pulmonar, que son de
   densidad de tejido blando y de otro modo quedarían excluidos por el
   umbral), cierre morfológico (suaviza la superficie pleural, reincorpora
   estructuras yuxtapleurales), y luego se reaplica el filtro de mayor
   componente ya que el cierre puede introducir pequeñas islas espurias.

**Por qué no un modelo aprendido:** la separación de HU entre pulmón y
tejido blando (>500 HU) es lo bastante grande como para que el umbralizado
clásico sea a la vez más simple y más auditable que una red, sin ninguna
pérdida de precisión para esta población.

**Modos de fallo conocidos:** un enfisema severo o un neumotórax cambian
el número/forma de componente esperado; el derrame pleural (líquido, no
aire) no se segmenta mediante un umbral de aire y necesitaría un enfoque
separado.

## Corazón

**Algoritmo:** level set de contorno activo geodésico (GAC) con conciencia
de bordes.

1. **Preprocesamiento** (`organs/heart/preprocessing.py`): recorte a una
   ROI mediastínica (`roi_x/y/z_fraction`, una heurística de espacio de
   coordenadas que sustituye a un registro con atlas), remuestreo a
   espaciado isotrópico, eliminación de ruido.
2. **Segmentación** (`organs/heart/segmentation.py`):
   - Magnitud del gradiente de la ROI (`gradient_sigma_mm`).
   - Mapeo sigmoide del gradiente a una imagen de velocidad en `[0, 1]`:
     cercana a 1 en regiones interiores homogéneas, cercana a 0 en bordes
     fuertes.
   - Semilla automática en el centroide de los voxeles en rango de tejido
     blando (`seed_hu_range`, por defecto 0–100 HU, miocardio/pool
     sanguíneo sin realce) dentro de la ROI.
   - Inicialización del level set como una función de distancia con signo
     de una pequeña esfera (`initial_sphere_radius_mm`) alrededor de la
     semilla.
   - Evolución con `sitk.GeodesicActiveContourLevelSetImageFilter`
     (`propagation_scaling`, `curvature_scaling`, `advection_scaling`,
     `max_iterations`, `max_rms_error`); umbralización del resultado en 0.
3. **Postprocesamiento** (`organs/heart/postprocessing.py`): se conserva el
   único componente más grande, relleno de huecos, cierre morfológico.

**Por qué no un umbral:** la HU del miocardio/pool sanguíneo (sin realce,
aproximadamente 0–100) se superpone con los grandes vasos, el límite de la
grasa pericárdica y el diafragma. Un umbral puro se filtra hacia la aorta/
vena cava y más allá — exactamente el modo de fallo que el trabajo previo
del proyecto señaló como necesitado de segmentación con conciencia de
bordes. El level set, en cambio, se detiene en los *bordes* de la imagen
(magnitud de gradiente alta → velocidad cercana a cero), que es donde en
realidad se encuentra el límite anatómico verdadero, sin importar la HU a
cada lado de él.

**Modos de fallo conocidos:** esto segmenta toda la silueta cardíaca
(cámaras + miocardio + muñones de los grandes vasos adheridos), no cámara
por cámara; un gradiente endocárdico/epicárdico muy débil (adquisiciones
delgadas, de baja dosis o borrosas por movimiento) puede quedarse corto o
sobrepasar el límite verdadero y necesita reajuste de
`advection_scaling`/`curvature_scaling`.

### Corazón — variante de tomografía por síncrotrón ex-vivo

`configs/heart_synchrotron.yaml`, `modality="synchrotron"` en
`organs/heart/{preprocessing,segmentation}.py`.

La TC clínica sin contraste no son los únicos datos reales contra los que
se ha validado este proyecto. El proyecto ESRF Human Organ Atlas / HiP-CT
(https://human-organ-atlas.esrf.fr) publica tomografía por síncrotrón de
contraste de fase ex-vivo de órganos donados — un espécimen (corazón
LADAF-2021-17, resolución de visión general de 169.36 µm, 870×870×1020
voxeles) se usó para validar esta rama. Es una adquisición genuinamente
distinta, no solo una TC de mayor resolución, así que tiene su propio
algoritmo en lugar de un simple ajuste de configuración sobre el de TC:

1. **Preprocesamiento**: el espécimen se encuentra dentro de un tubo
   portamuestras cilíndrico. La pared del tubo es *más densa* que el
   tejido de interés, así que ningún umbral de intensidad podría separar
   "tejido" de "tubo" — en su lugar, el tubo se excluye geométricamente,
   recortando cada corte a un círculo (`tube_radius_fraction`) del tamaño
   de su pared interior.
2. **Segmentación**: un umbral de intensidad simple
   (`tissue_intensity_threshold`) más apertura morfológica (eliminación de
   ruido) más componente conexa más grande. La tomografía por contraste de
   fase ex-vivo tiene un contraste de tejido blando dramáticamente mejor
   que la TC clínica — el medio de montaje de fondo y el tejido ya están
   bien separados una vez eliminado el tubo — así que el level set con
   conciencia de bordes que necesita la rama de TC estaría resolviendo un
   problema que esta modalidad no tiene.
3. **Postprocesamiento**: el mismo cierre + relleno de huecos que la rama
   de TC, solo que con un radio físico mucho menor
   (`morphological_closing_radius_mm: 0.35`) para adaptarse a voxeles ~9
   veces más finos.
4. **Reparación de malla**: los datos reales, ruidosos y de alta
   resolución producen una superficie de alto género (muchos pequeños
   túneles topológicos por el ruido del umbralizado) que
   `trimesh.repair.fill_holes` por sí solo no siempre puede cerrar.
   `core/mesh_ops.py::repair_mesh` recurre a
   [pymeshfix](https://github.com/pyvista/pymeshfix) (Attene, 2010) cuando
   la reparación de trimesh no logra la estanqueidad — esto fue lo que
   realmente llevó la reconstrucción de LADAF-2021-17 a una malla cerrada
   válida.

**Cargar estos datos:** se distribuyen como un directorio o `.zip` de
imágenes de corte 2D (JP2/TIFF/PNG), no DICOM/NIfTI, y no llevan metadatos
fiables de espaciado en los propios archivos:

```bash
python main.py --input path/to/slices_or.zip --organ heart \
    --modality synchrotron --spacing 0.16936 0.16936 0.16936
```

El conjunto de datos crudo (~150MB comprimido) no se incluye en este
repositorio — ver docs/VALIDATION.md para saber por qué y cómo
reproducirlo tú mismo.

**Modos de fallo conocidos:** `tissue_intensity_threshold` y
`tube_radius_fraction` están calibrados para este espécimen y esta
configuración de escáner específicos (intensidad nativa de 16 bits, no una
unidad física portable como las Unidades Hounsfield) — un espécimen o
adquisición distintos necesitarán una verificación de histograma de corte
antes de reutilizar estos valores por defecto; no se espera que el volumen
reconstruido de un espécimen ex-vivo fijado/conservado caiga dentro del
rango de plausibilidad de paciente vivo en `core/validation.py` (el tejido
se contrae con la fijación), así que una marca de "no plausible" ahí es lo
esperado, no un error.

## Hígado

**Algoritmo:** crecimiento de regiones por conectividad de confianza con
semilla.

1. **Preprocesamiento** (`organs/liver/preprocessing.py`): recorte a una
   ROI del cuadrante superior derecho, remuestreo, eliminación de ruido.
2. **Segmentación** (`organs/liver/segmentation.py`): semilla automática en
   el centroide de los voxeles en `seed_hu_range` (por defecto 20–70 HU)
   dentro de la ROI, luego crecimiento con
   `sitk.ConfidenceConnectedImageFilter` (`confidence_multiplier`,
   `confidence_iterations`,
   `confidence_initial_neighborhood_radius`) — en cada iteración se
   reestima la media/desviación estándar actual de la región y se añaden
   los vecinos dentro de `multiplier` desviaciones estándar.
3. **Postprocesamiento** (`organs/liver/postprocessing.py`): componente más
   grande, relleno de huecos, cierre morfológico.

**Por qué crecimiento de regiones y no un umbral:** el parénquima hepático
es bastante homogéneo pero no *único* en intensidad — se superpone con la
HU del bazo, el riñón y el músculo. Un umbral global sobre- o
sub-segmenta según qué más haya en el abdomen a esa HU. El crecimiento de
regiones desde un punto conocido (vía el prior de ROI) como interior al
hígado, adaptándose a las estadísticas locales en lugar de a una banda
fija, es lo que alcanzó un Dice de 0.918 en trabajo previo del proyecto
referenciado en las notas de diseño de este proyecto.

**Modos de fallo conocidos:** el filtro de conectividad de confianza puede
filtrarse a través de un límite delgado y de bajo contraste hacia el
diafragma o un órgano directamente adyacente si la semilla de la ROI cae
demasiado cerca de ese límite; los hígados cirróticos o muy heterogéneos
(realce por contraste, lesiones) violan el supuesto de "parénquima
razonablemente homogéneo" del que depende el crecimiento de regiones.

### Hígado — variante de tomografía por síncrotrón ex-vivo

`configs/liver_synchrotron.yaml`, `modality="synchrotron"` en
`organs/liver/{preprocessing,segmentation}.py`.

Validado contra un espécimen real del ESRF Human Organ Atlas / HiP-CT
(hígado LADAF-2021-17, resolución de visión general de 180.48 µm,
1140×1140×1238 voxeles — el volumen nativo más grande de los cinco
órganos de este proyecto, ~1.6 mil millones de voxeles).

1. **Preprocesamiento**: a diferencia del corazón y el cerebro, el
   espécimen de hígado llena el cuadro sin margen visible de tubo
   portamuestras (verificado contra el archivo real: las poblaciones de
   voxeles de esquina y centro son del mismo orden de magnitud, no el
   contraste medio-vs-aire del que depende el recorte de tubo del
   corazón/cerebro) — así que aquí no hace falta exclusión geométrica de
   tubo, solo downsampling (`downsample_factor: 3`, necesario por el
   tamaño nativo).
2. **Segmentación**: umbral de intensidad simple
   (`tissue_intensity_threshold: 18300`, calibrado contra un histograma
   del corte medio del archivo real: un pico dominante de medio de montaje
   en 17200–18200 unidades nativas, y una población de tejido separada en
   19100–21000) más apertura morfológica más componente conexa más grande
   — misma lógica que la rama síncrotrón del corazón.
3. **Postprocesamiento / reparación de malla**: igual que la rama síncrotrón
   del corazón.

**Modos de fallo conocidos:** igual que el corazón — los umbrales están
calibrados por espécimen/escáner, y el volumen ex-vivo puede caer fuera del
rango de plausibilidad en vivo por fijación/preservación.

## Riñones

**Algoritmo:** level set de contorno activo geodésico bilateral con
conciencia de bordes (misma clase de algoritmo que el corazón,
implementado de forma independiente — ver `docs/ARCHITECTURE.md` para
entender por qué compartir el *tipo* de técnica no es lo mismo que
compartir una rutina de segmentación).

1. **Preprocesamiento** (`organs/kidneys/preprocessing.py`): recorte a una
   ROI del abdomen posterior que abarca ambos flancos.
2. **Segmentación** (`organs/kidneys/segmentation.py`): se calcula la
   imagen de gradiente/velocidad una sola vez para la ROI compartida; se
   encuentran dos semillas de forma independiente (centroide de los
   voxeles de `seed_hu_range` en la mitad izquierda y la mitad derecha de
   la ROI); se evolucionan dos level sets independientes desde esas
   semillas contra la misma imagen de velocidad; se unen los resultados.
3. **Postprocesamiento** (`organs/kidneys/postprocessing.py`): se conservan
   los dos componentes más grandes (riñón izquierdo + derecho), relleno de
   huecos, cierre morfológico.

**Por qué no un umbral:** la HU del parénquima renal sin realce (~30–60)
se superpone con el músculo psoas y órganos adyacentes — la misma clase de
problema que el corazón, de ahí la misma clase de solución.

**Modos de fallo conocidos:** un riñón en herradura o una nefrectomía
unilateral rompen el supuesto de "exactamente dos componentes" del
postprocesamiento; una hidronefrosis significativa (sistema colector lleno
de líquido) cambia la homogeneidad de HU interna que asume la función de
velocidad del level set.

### Riñones — variante de tomografía por síncrotrón ex-vivo

`configs/kidneys_synchrotron.yaml`, `modality="synchrotron"` en
`organs/kidneys/{preprocessing,segmentation}.py`.

Validado contra un espécimen real del ESRF Human Organ Atlas / HiP-CT
(riñón K292, resolución de visión general de 163.52 µm, 600×600×931
voxeles). A diferencia de la rama clínica, este archivo es un **único**
riñón excisado, no un par bilateral in-situ — así que la lógica de doble
semilla de la variante de TC no aplica.

1. **Preprocesamiento**: igual que el hígado — el espécimen llena el
   cuadro sin margen de tubo visible, así que solo hace falta downsampling
   (`downsample_factor: 1`, ya que el volumen nativo, ~335 millones de
   voxeles, es menor que el del corazón incluso antes de reducir).
2. **Segmentación**: umbral de intensidad simple
   (`tissue_intensity_threshold: 44300`, calibrado contra un histograma
   del corte medio del archivo real: un pico dominante de medio de montaje
   en 42600–43600 unidades nativas, y una población de tejido separada en
   43600–45600 — este espécimen lee mucho más alto en intensidad nativa
   que los demás archivos) más apertura morfológica más componente conexa
   más grande.
3. **Postprocesamiento**: `num_components: 1` (no los 2 de la variante de
   TC) — solo hay un riñón que encontrar.

**Modos de fallo conocidos:** igual que el corazón/hígado — umbrales
calibrados por espécimen/escáner, volumen ex-vivo potencialmente fuera del
rango de plausibilidad en vivo.

## Cerebro

**Algoritmo:** umbral + componente conexa más grande (**solo** tomografía
por síncrotrón ex-vivo — este proyecto no incluye un pipeline clínico de
TC/RM para cerebro).

`configs/brain_synchrotron.yaml`, `organs/brain/{preprocessing,segmentation,postprocessing}.py`.

No existe una rama de TC/RM clínica aquí: la segmentación de tejido
cerebral a partir de imagen clínica (skull-stripping más segmentación de
parénquima) es un problema bien estudiado por sí mismo, y construir uno sin
datos etiquetados contra los cuales validarlo no cumpliría el estándar de
rigor de este proyecto — ver `organs/brain/preprocessing.py` y
`docs/ARCHITECTURE.md`. `main.py` rechaza explícitamente
`--organ brain` con cualquier modalidad que no sea `synchrotron`.

Validado contra un espécimen real del ESRF Human Organ Atlas / HiP-CT
(cerebro LADAF-2021-17, resolución de visión general de 169.6 µm,
803×803×970 voxeles).

1. **Preprocesamiento**: a diferencia del hígado/riñón, un escaneo
   "órgano completo" de cerebro llena casi todo el tubo portamuestras con
   tejido — no hay un medio de montaje de baja densidad separado que
   umbralizar. El único prior geométrico necesario es excluir el tubo en
   sí, igual que en el corazón (`tube_radius_fraction: 0.485`, medido
   empíricamente barriendo radios candidatos y comprobando dónde la
   fracción de voxeles no nulos justo fuera de cada uno deja de ser 1.0).
2. **Segmentación**: umbral de intensidad
   (`tissue_intensity_threshold: 5000`) más apertura morfológica más
   componente conexa más grande. Un histograma del corte de calibración
   muestra una distribución de tejido claramente **bimodal**: una primera
   población en ~3700–4500 (medio de montaje/fluido llenando los surcos
   entre circunvoluciones) y una segunda, más grande, en ~5100–7900
   (parénquima cerebral real), con un valle alrededor de 4900–5000. Un
   umbral de 2000 (usado en una versión anterior de esta configuración)
   caía por debajo de *ambas* poblaciones, fusionándolas en una masa
   cilíndrica sólida sin circunvoluciones ni surcos visibles — verificado
   visualmente comparando el umbralizado de un corte real a distintos
   valores. 5000 se sitúa en el valle, conservando corteza y sustancia
   blanca mientras excluye el fluido de los surcos, lo que sí recupera una
   superficie cortical plegada reconocible.
3. **Postprocesamiento / reparación de malla**: igual que el resto de las
   ramas síncrotrón.

**Modos de fallo conocidos:** igual que el resto de las ramas síncrotrón —
umbrales calibrados por espécimen/escáner (y, para este órgano en
particular, sensibles a dónde cae exactamente el valle entre las
poblaciones bimodales del histograma); el volumen reconstruido (~1109 mL
en el espécimen validado) cae dentro del rango de plausibilidad en vivo
(1000–1600 mL), aunque para otros especímenes/escáneres podría caer fuera
por las mismas razones de fijación/preservación que el resto de los
especímenes ex-vivo de este proyecto.
</content>
