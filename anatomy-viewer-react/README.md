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

1. Copia tu archivo `.glb` (o `.gltf` + sus texturas/bin) dentro de
   `public/models/`. Por ejemplo: `public/models/sistema-cardiorrespiratorio.glb`.
2. Abre `src/App.jsx` y actualiza la constante `MODEL_URL` con el nombre de
   tu archivo:

   ```js
   const MODEL_URL = "/models/sistema-cardiorrespiratorio.glb";
   ```

   Todo lo que pongas en `public/` se sirve tal cual desde la raíz (`/`), así
   que un archivo en `public/models/x.glb` se referencia como `/models/x.glb`.

No hace falta ningún registro adicional: `Model.jsx` recorre el modelo
completo con `useGLTF` y detecta clics/hover sobre cualquier malla que
tenga, sin importar cuántas sean.

## 3. Por qué el modelo tiene que estar separado por piezas

El código identifica cada estructura por el **nombre de la malla**
(`mesh.name`, el nombre del objeto tal como quedó en el archivo `.glb`). Si
tu corazón es un solo bloque sólido, todo el corazón se resaltará y
seleccionará como una sola pieza — no podrás distinguir la aorta de la
aurícula derecha.

Para separar un modelo descargado como una sola malla:

1. Impórtalo en **Blender**.
2. Selecciona la malla, entra en modo Edición (`Tab`), y usa
   `Mesh → Separate → By Loose Parts` (si las piezas ya están desconectadas
   entre sí en la geometría) o separa manualmente selecciones de caras con
   `P → Selection`.
3. Renombra cada pieza resultante desde el Outliner (doble clic sobre el
   nombre) usando los mismos `id` que ya están en
   `src/data/estructuras.json` (p. ej. `corazon`, `aorta`,
   `auricula_derecha`, `valvula_mitral`...). No es obligatorio que coincida
   carácter por carácter: `src/utils/matchStructure.js` normaliza acentos,
   mayúsculas y guiones antes de comparar, y también revisa la lista
   `meshNames` de cada estructura por si prefieres dejar los nombres en
   inglés o como los trae el modelo original.
4. Si el modelo es pesado, aplica un modificador **Decimate** antes de
   exportar, y usa **Shade Smooth** si se ve poligonal.
5. Exporta con `File → Export → glTF 2.0 (.glb)`, con la opción de mantener
   los nombres de los objetos activada (viene así por defecto).

Si haces clic sobre una malla cuyo nombre no está en `estructuras.json`, el
panel lateral igual se abre y te muestra el nombre exacto de esa malla —
así sabes qué `id` o alias agregar.

## 4. Completar el contenido educativo

Cada entrada de `src/data/estructuras.json` tiene esta forma:

```json
{
  "id": "aorta",
  "nombre": "Aorta",
  "meshNames": ["aorta", "arteria_aorta"],
  "conocimientoPrevio": "",
  "conocimientoNuevo": "",
  "aplicacionClinica": "",
  "imagenUrl": ""
}
```

- `id`: identificador interno, usado como primer criterio de coincidencia
  con el nombre de la malla.
- `nombre`: lo que se muestra como título del panel.
- `meshNames`: alias adicionales para cuando el nombre real de la malla no
  coincide con `id` (útil si no vas a renombrar mallas en Blender).
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
tráquea, bronquios, bronquiolos, alveolos y pulmones.

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
    ├── App.jsx            ← estado (estructura seleccionada/hover) + layout
    ├── main.jsx
    ├── index.css          ← directivas de Tailwind
    ├── components/
    │   ├── Scene.jsx      ← Canvas, luces, OrbitControls
    │   ├── Model.jsx      ← carga del .glb, raycasting, resaltado hover
    │   └── InfoPanel.jsx  ← panel lateral (Cuadro de Conocimiento)
    ├── data/
    │   └── estructuras.json
    └── utils/
        └── matchStructure.js  ← empareja mesh.name con una entrada del JSON
```

## 6. Compilar para producción

```bash
npm run build
```

Genera `dist/`, listo para servir como sitio estático (por ejemplo, en el
mismo Vercel/GitHub Pages que ya usa el resto del repositorio, apuntando a
esta carpeta como su propio proyecto).
