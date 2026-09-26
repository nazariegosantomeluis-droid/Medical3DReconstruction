# Visor anatómico 3D — Sistema cardiorrespiratorio

Visor interactivo hecho con React, React Three Fiber (Three.js) y Tailwind
CSS. Carga un modelo `.glb`/`.gltf` con las estructuras cardiorrespiratorias
como mallas separadas, resalta la malla bajo el cursor y, al hacer clic,
abre un panel lateral con el "Cuadro de Conocimiento" de esa estructura.

## 1. Instalar y correr

```bash
cd anatomy-viewer-react
npm install
npm run dev
```

Abre la URL que imprime Vite (por defecto `http://localhost:5173`).

## 2. Colocar tu modelo 3D

1. Copia tu archivo `.glb` dentro de `public/models/`, con el nombre
   `corazon-segmentado.glb` (o cambia la constante `MODEL_URL` en
   `src/App.jsx` si prefieres otro nombre).
2. Recarga la página. Si el archivo no existe o no carga, el visor muestra
   un aviso claro ("Todavía no hay un modelo 3D cargado") en vez de una
   pantalla en blanco — no es un bug, es que falta el paso 1.

Todo lo que pongas en `public/` se sirve tal cual desde la raíz del sitio,
así que un archivo en `public/models/x.glb` se referencia como
`/models/x.glb` (o `<BASE_URL>models/x.glb` si el sitio vive en una subruta,
que es justo lo que hace `MODEL_URL` en `App.jsx`).

## 3. Cómo se consiguió un modelo ya separado por piezas (sin Blender)

El código identifica cada estructura por el **nombre de la malla**
(`mesh.name`). Un modelo escaneado/fotogrametría (como el que se probó
primero) suele venir como una sola malla fusionada — click en cualquier
parte selecciona "todo el corazón" y no se puede distinguir la aorta de la
aurícula derecha. La solución no fue separar eso a mano en Blender, sino
usar una fuente que **ya viene separada por estructura, con nombres
anatómicos reales**:

- Fuente: [BodyParts3D / Anatomography 4.3](https://github.com/olivercase/body_parts_3d_api),
  © Database Center for Life Science (DBCLS), licencia **CC BY-SA 2.1
  Japan** (si publicas el `.glb` resultante, debes mantener esta
  atribución y licencia para el modelo).
- `scripts/build_corazon_segmentado.py` (en la raíz de este visor) fusiona
  ~106 mallas `.obj` de ese dataset en las 23 estructuras pedidas —
  por ejemplo, la "Aorta" se arma uniendo `Ascending aorta` + `Arch of
  aorta` + `Descending aorta`, y las "Arterias coronarias" fusionan sus
  ~15 ramas en una sola pieza — y exporta un único `.glb` con un nodo por
  estructura, ya nombrado exactamente como lo espera
  `src/data/estructuras.json`.
- 4 de las 23 estructuras (`pericardio`, `nariz`, `bronquiolos`,
  `alveolos`) **no tienen malla propia**: el pericardio y la nariz no
  están modelados en este atlas, y bronquiolos/alveolos son microscópicos
  — ningún atlas anatómico macro los representa como malla 3D. Quedan
  como nodos "solo concepto": tienen su ficha en el Cuadro de Conocimiento
  y aparecen en el mapa de conexiones, pero no se puede hacer clic en
  ellas en el visor 3D (marcadas `sinMalla: true` en `estructuras.json`).

Para regenerar o ajustar el `.glb` (corre esto desde dentro de
`anatomy-viewer-react/`, donde ya viven `build_corazon_segmentado.py` y
`lfs_include_pattern.txt`):

```bash
git clone https://github.com/olivercase/body_parts_3d_api.git
cp build_corazon_segmentado.py lfs_include_pattern.txt body_parts_3d_api/
cd body_parts_3d_api
git lfs install
git lfs pull --include="$(cat lfs_include_pattern.txt)"   # solo las ~106 piezas necesarias
pip install trimesh numpy
python3 build_corazon_segmentado.py
cp corazon-segmentado.glb ../public/models/
```

`lfs_include_pattern.txt` y `build_corazon_segmentado.py` describen
exactamente qué IDs de malla (`FJ####`) entran en cada una de las 18
estructuras con malla, vía expresiones regulares sobre el nombre
anatómico oficial (columna `name` de `MANIFEST.csv` en ese repositorio).

Si haces clic sobre una malla cuyo nombre no está en `estructuras.json`, el
panel lateral igual se abre y te muestra el nombre exacto de esa malla —
así sabes qué `id` o alias agregar. También puedes activar el botón
**"Modo Debug"** (arriba a la derecha) para ver, sin necesidad de abrir el
modelo en ningún programa externo, el inventario completo de nombres de
malla apenas carga el archivo.

### `corazon`: un cuerpo real distinto, no "sin malla"

`corazon` sí tiene malla propia: la del corazón completo, reconstruido a
partir de un espécimen ex-vivo real (micro-CT sincrotrón, LADAF-2021-17)
por el pipeline Python de este mismo repositorio — ya visible en
`docs/index.html`, el visor original. `extract_heart_mesh.py` la saca de
ahí, y `merge_real_heart.py` la agrega a `corazon-segmentado.glb` como una
19ª pieza.

Pero ese espécimen y el atlas BodyParts3D son **dos cuerpos reales
distintos que no comparten coordenadas** — superponerlos haría que las
válvulas y cámaras del atlas parezcan encajar dentro de este corazón
específico, cuando en realidad son de otra persona. Por eso cada una vive
en su propio nodo-grupo dentro del `.glb` (`grupo_especimen_real` /
`grupo_atlas_bodyparts3d`, ver `src/constants/modelGroups.js`), y el
visor solo muestra uno a la vez: seleccionar `corazon` cambia al
espécimen completo y reencuadra la cámara a él; seleccionar cualquier
otra estructura vuelve al grupo del atlas. Esto es automático — no hace
falta ninguna acción extra al generar el `.glb`, siempre que
`merge_real_heart.py` se corra sobre el archivo que ya tiene las 18
piezas del atlas (lee `docs/index.html`, así que ese archivo debe existir
y tener datos reales de corazón).

## 4. Completar el contenido educativo y el mapa de conexiones

Cada entrada de `src/data/estructuras.json` tiene esta forma:

```json
{
  "id": "aorta",
  "nombre": "Aorta",
  "meshNames": ["aorta", "arteria_aorta"],
  "sistema": "cardiovascular",
  "relacionadas": ["ventriculo_izquierdo", "valvula_aortica", "arterias_coronarias"],
  "conocimientoPrevio": "",
  "conocimientoNuevo": "",
  "aplicacionClinica": "",
  "imagenUrl": ""
}
```

- `id`: identificador interno; también el `node_name` que trae el `.glb`
  generado por `build_corazon_segmentado.py`.
- `nombre`: lo que se muestra como título del panel.
- `meshNames`: alias adicionales para cuando el nombre real de la malla no
  coincide con `id` (`src/utils/matchStructure.js` normaliza acentos,
  mayúsculas y guiones antes de comparar).
- `sistema`: `"cardiovascular"` o `"respiratorio"` — agrupa el índice
  lateral ("Ver todas las estructuras").
- `relacionadas`: ids de otras estructuras conectadas anatómica o
  fisiológicamente — son los chips de "Estructuras relacionadas" del
  panel (el mapa de conexiones clínicas). Al hacer clic en un chip, el
  panel salta a esa estructura y, si tiene malla real cargada, también se
  resalta en el visor 3D aunque el cursor nunca haya pasado por ahí.
- `grupo` (opcional): `"atlas_bodyparts3d"` o `"especimen_real"` — a cuál
  de los dos especímenes reales del `.glb` pertenece esta malla (ver
  sección 3). Seleccionar una estructura con `grupo` distinto al que está
  visible cambia el grupo activo y reencuadra la cámara a él.
- `sinMalla` (opcional): `true` en las 4 estructuras sin pieza propia
  (ver sección 3) — el chip se muestra con borde punteado y sigue siendo
  navegable, solo que no resalta nada en 3D.
- `notaSinMalla` (opcional): el texto que explica por qué esa estructura
  no tiene malla, mostrado arriba del Cuadro de Conocimiento.
- `notaEspecimen` (opcional): igual que `notaSinMalla`, pero para aclarar
  que una estructura viene de un espécimen real distinto a las demás (lo
  usa `corazon`).
- `conocimientoPrevio`, `conocimientoNuevo`, `aplicacionClinica`: los tres
  bloques de texto del Cuadro de Conocimiento. Van vacíos a propósito —
  complétalos con tu propio contenido de estudio.
- `imagenUrl`: URL de una imagen ilustrativa opcional (si la dejas vacía,
  el panel simplemente no muestra imagen).

Ya están precargadas las 23 estructuras pedidas: corazón, venas cavas,
aorta, arterias pulmonares, venas pulmonares, aurícula derecha, aurícula
izquierda, ventrículo derecho, ventrículo izquierdo, válvula aórtica,
válvula pulmonar, válvula bicúspide (mitral), válvula tricúspide,
pericardio, arterias coronarias, venas coronarias, nariz, laringe,
tráquea, bronquios, bronquiolos, alveolos y pulmones — con `relacionadas`
ya completado para las 23. Los tres campos de contenido de estudio quedan
vacíos para que los llenes tú.

## 5. Estructura del proyecto

```
anatomy-viewer-react/
├── index.html
├── package.json
├── tailwind.config.js
├── vite.config.js
├── public/
│   └── models/            ← coloca aquí tu .glb
└── src/
    ├── App.jsx                  ← estado (selección/hover/debug) + layout
    ├── main.jsx
    ├── index.css                ← directivas de Tailwind
    ├── components/
    │   ├── Scene.jsx            ← Canvas, luces, OrbitControls
    │   ├── Model.jsx            ← carga del .glb, raycasting, resaltado hover/forzado
    │   ├── InfoPanel.jsx        ← Cuadro de Conocimiento + mapa de conexiones
    │   ├── StructureIndex.jsx   ← índice "Ver todas las estructuras"
    │   ├── DebugPanel.jsx       ← inventario de mallas del Modo Debug
    │   └── ModelErrorBoundary.jsx  ← aviso claro si el .glb no carga
    ├── data/
    │   └── estructuras.json
    └── utils/
        └── matchStructure.js    ← empareja mesh.name con una entrada del JSON
```

## 6. Compilar para producción

```bash
npm run build
```

Genera `dist/`, listo para servir como sitio estático (por ejemplo, en el
mismo Vercel/GitHub Pages que ya usa el resto del repositorio, apuntando a
esta carpeta como su propio proyecto).
