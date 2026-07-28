#!/usr/bin/env python3
"""Build the published interactive HTML demo (5 organs, real data where the
repository has it) from the payload produced by build_demo_payload.py.

Usage:
    python scripts/build_demo_payload.py --output /tmp/payload.json
    python scripts/build_interactive_artifact.py --payload /tmp/payload.json --output /tmp/medical3d_viewer.html

This is a dev utility for the chat-published demo artifact, kept separate
from the CLI's own single-organ export (medical3d.core.html_viewer, used by
``main.py --visualize html``) because the demo's scope — five organs
switchable in one page, all within the ~16MB artifact-publishing budget —
is specific to that presentation context, not a pipeline output.
"""

from __future__ import annotations

import argparse
import json
import os

ORGAN_ORDER = ["lungs", "heart", "liver", "kidneys", "brain"]

ORGAN_META = {
    "lungs": {
        "label": "Pulmones",
        "algo": "Umbral + componentes conectados",
        "color_hex": "#e8b4b8",
        "source_note": (
            "Reconstruido a partir de una tomografía de tórax real incluida en el "
            "repositorio (data/volumes/CTChest.nrrd)."
        ),
        "caveat": (
            "Alta fidelidad: el pulmón aireado supera los 500 HU, claramente separado "
            "de todo tejido circundante, por lo que el límite segmentado es la "
            "superficie anatómica real, no una aproximación."
        ),
        "anatomy": (
            "Los pulmones son un par de órganos esponjosos alojados en la caja torácica, "
            "responsables del intercambio de oxígeno y dióxido de carbono con la sangre. "
            "El pulmón derecho tiene tres lóbulos y el izquierdo dos (para dejar espacio "
            "al corazón), y juntos contienen unos 300-500 millones de alvéolos. El aire "
            "aireado es mucho menos denso (radiotransparente) que el resto del cuerpo, "
            "lo que hace que el pulmón sea uno de los órganos más fáciles de segmentar "
            "por umbral en una tomografía computarizada."
        ),
        "initial_theta": 0.6,
        "initial_phi": 1.15,
    },
    "heart": {
        "label": "Corazón",
        "algo": "Umbral + componente conectado (ex-vivo)",
        "color_hex": "#c0392b",
        "source_note": (
            "Reconstruido a partir de un espécimen ex-vivo real (LADAF-2021-17, "
            "resolución 169.36µm) del proyecto ESRF Human Organ Atlas / HiP-CT — "
            "tomografía sincrotrón de contraste de fase, no una tomografía clínica."
        ),
        "caveat": (
            "Este pipeline también admite tomografía clínica (in-vivo) mediante un "
            "level set sensible a bordes, usado porque la CT clínica sin contraste "
            "carece del contraste de tejido blando que sí tiene este escaneo ex-vivo. "
            "El volumen reconstruido refleja un espécimen fijado/preservado, más "
            "pequeño que un corazón vivo — esperado, no un error."
        ),
        "anatomy": (
            "El corazón es una bomba muscular de cuatro cámaras (dos aurículas, dos "
            "ventrículos) que impulsa la sangre por el circuito pulmonar y el sistémico. "
            "Pesa entre 250 y 350 g en un adulto vivo y su volumen fisiológico típico "
            "ronda 300-900 mL según la fase del ciclo cardíaco. La reconstrucción de "
            "este proyecto proviene de tomografía sincrotrón ex-vivo, que resuelve "
            "detalle anatómico (paredes miocárdicas, vasos) muy superior al que permite "
            "una tomografía clínica sin contraste — a cambio, el volumen de un "
            "espécimen fijado es menor que el de un corazón latiendo, así que caer "
            "fuera del rango fisiológico en vivo es un resultado esperado, no un fallo "
            "del pipeline."
        ),
        "initial_theta": 0.6,
        "initial_phi": 1.15,
    },
    "liver": {
        "label": "Hígado",
        "algo": "Umbral + componente conectado (ex-vivo)",
        "color_hex": "#b9793f",
        "source_note": (
            "Reconstruido a partir de un espécimen ex-vivo real (LADAF-2021-17, "
            "resolución 180.48µm) del proyecto ESRF Human Organ Atlas / HiP-CT."
        ),
        "caveat": (
            "Este pipeline también admite tomografía clínica (in-vivo) mediante "
            "crecimiento de región con semilla (ConfidenceConnected). El volumen "
            "ex-vivo puede caer fuera del rango fisiológico en vivo por la misma razón "
            "que el corazón: un espécimen fijado no tiene el mismo volumen que el "
            "órgano en un paciente vivo."
        ),
        "anatomy": (
            "El hígado es el órgano sólido interno más grande del cuerpo, ubicado en el "
            "cuadrante superior derecho del abdomen, justo bajo el diafragma. Tiene dos "
            "lóbulos principales muy asimétricos (el derecho mucho mayor que el "
            "izquierdo) y cumple cientos de funciones metabólicas: síntesis de "
            "proteínas plasmáticas, producción de bilis, desintoxicación, y "
            "almacenamiento de glucógeno. En un adulto vivo su volumen típico es de "
            "1000-2500 mL. La reconstrucción de este proyecto usa la misma tomografía "
            "sincrotrón ex-vivo de alta resolución que el corazón y el riñón."
        ),
        "initial_theta": 0.6,
        "initial_phi": 1.15,
    },
    "kidneys": {
        "label": "Riñones",
        "algo": "Umbral + componente conectado (ex-vivo)",
        "color_hex": "#a8447a",
        "source_note": (
            "Reconstruido a partir de un espécimen ex-vivo real (K292, resolución "
            "163.52µm) del proyecto ESRF Human Organ Atlas / HiP-CT — un único riñón "
            "excisado, no un par bilateral in-situ."
        ),
        "caveat": (
            "Este pipeline también admite tomografía clínica (in-vivo) mediante un "
            "level set bilateral (busca ambos riñones a la vez). El espécimen real "
            "usado aquí es un solo riñón, así que la variante ex-vivo simplifica esa "
            "lógica bilateral: hay exactamente un objeto que encontrar."
        ),
        "anatomy": (
            "Los riñones son un par de órganos con forma de frijol, ubicados en el "
            "retroperitoneo (detrás del peritoneo, a ambos lados de la columna), cada "
            "uno con un peso de 115-190 g. Filtran la sangre para eliminar desechos "
            "metabólicos y regulan el balance de agua, electrolitos y presión arterial "
            "mediante la formación de orina en aproximadamente un millón de nefronas "
            "por riñón. En un adulto vivo el volumen combinado típico es 200-450 mL. "
            "Este proyecto reconstruye un único riñón ex-vivo de altísima resolución, "
            "donde se distinguen corteza y médula renal."
        ),
        "initial_theta": 3.14,
        "initial_phi": 1.15,
    },
    "brain": {
        "label": "Cerebro",
        "algo": "Umbral + componente conectado (ex-vivo)",
        "color_hex": "#c9a0dc",
        "source_note": (
            "Reconstruido a partir de un espécimen ex-vivo real (LADAF-2021-17, "
            "resolución 169.6µm) del proyecto ESRF Human Organ Atlas / HiP-CT."
        ),
        "caveat": (
            "Este proyecto NO incluye un pipeline clínico de CT/MRI para cerebro: la "
            "segmentación de tejido cerebral (skull-stripping + parénquima) a partir de "
            "imagen clínica es un problema bien estudiado por sí mismo, y construir uno "
            "sin datos etiquetados contra los cuales validarlo no cumpliría el estándar "
            "de rigor de este proyecto. El cerebro solo se reconstruye a partir de "
            "tomografía sincrotrón ex-vivo."
        ),
        "anatomy": (
            "El cerebro es el órgano central del sistema nervioso, responsable de la "
            "cognición, el control motor, la percepción sensorial y la regulación "
            "autonómica. Se organiza en corteza cerebral (sustancia gris, muy plegada), "
            "sustancia blanca subcortical, cerebelo y tronco encefálico. En un adulto "
            "vivo su volumen típico es de 1000-1600 mL. La reconstrucción de este "
            "proyecto proviene de un escaneo \"órgano completo\" ex-vivo que resuelve "
            "circunvoluciones y estructuras internas con un detalle muy superior al de "
            "la neuroimagen clínica convencional — el volumen puede diferir del rango "
            "en vivo por las mismas razones de fijación/preservación que el resto de "
            "los especímenes ex-vivo de este proyecto."
        ),
        "initial_theta": 0.6,
        "initial_phi": 1.15,
    },
}


def build(payload: dict) -> str:
    viewer_data = {}
    for organ in ORGAN_ORDER:
        if organ not in payload:
            continue
        entry = payload[organ]
        viewer_data[organ] = {
            "mesh": entry["mesh"],
            "slices": entry["slices"],
            "metrics": entry["metrics"],
            "validation": entry["validation"],
        }

    available_organs = [o for o in ORGAN_ORDER if o in viewer_data]

    html = _TEMPLATE
    html = html.replace("__ORGAN_ORDER_JSON__", json.dumps(available_organs))
    html = html.replace("__ORGAN_META_JSON__", json.dumps({k: ORGAN_META[k] for k in available_organs}))
    html = html.replace("__VIEWER_DATA_JSON__", json.dumps(viewer_data))
    return html


_TEMPLATE = r"""<!doctype html>
<title>Medical3DReconstruction — Visor</title>
<style>
  :root {
    --bg: #0a0e13; --surface: #121820; --surface-raised: #1a222c; --border: #26313d;
    --text: #eaf0f6; --text-dim: #7e93a7; --text-faint: #4b5c6c;
    --accent: #46c9c2; --accent-soft: rgba(70,201,194,0.14); --accent-strong: #2f918c;
    --warn: #d99a3c; --ok: #4fbf78;
    --font-ui: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", "Helvetica Neue", sans-serif;
    --font-mono: ui-monospace, "SF Mono", "Cascadia Code", "Roboto Mono", "Consolas", monospace;
  }
  :root[data-theme="light"] {
    --bg: #eef2f5; --surface: #ffffff; --surface-raised: #f4f7f9; --border: #d7dfe5;
    --text: #121820; --text-dim: #566878; --text-faint: #94a3b0;
    --accent: #1f8f88; --accent-soft: rgba(31,143,136,0.10); --accent-strong: #17706b;
  }
  @media (prefers-color-scheme: light) {
    :root:not([data-theme="dark"]) {
      --bg: #eef2f5; --surface: #ffffff; --surface-raised: #f4f7f9; --border: #d7dfe5;
      --text: #121820; --text-dim: #566878; --text-faint: #94a3b0;
      --accent: #1f8f88; --accent-soft: rgba(31,143,136,0.10); --accent-strong: #17706b;
    }
  }
  * { box-sizing: border-box; }
  html, body { height: 100%; margin: 0; background: var(--bg); color: var(--text); font-family: var(--font-ui); overflow: hidden; }
  body { display: flex; flex-direction: column; }
  header { display: flex; align-items: center; gap: 0.75rem; padding: 0.7rem 1.1rem; background: var(--surface-raised); border-bottom: 1px solid var(--border); flex-shrink: 0; }
  header .mark { width: 9px; height: 9px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
  header h1 { font-size: 0.92rem; margin: 0; font-weight: 650; }
  header .spacer { flex: 1; }
  .tab-switch { display: flex; gap: 0.2rem; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 0.2rem; }
  .tab-btn { font-size: 0.76rem; font-weight: 600; padding: 0.35rem 0.75rem; border-radius: 6px; border: none; background: transparent; color: var(--text-dim); cursor: pointer; font-family: inherit; }
  .tab-btn[aria-selected="true"] { background: var(--accent-soft); color: var(--text); }
  .icon-btn-flat { padding: 0.35rem 0.6rem; border-radius: 7px; border: 1px solid var(--border); background: var(--surface); color: var(--text-dim); font-size: 0.72rem; cursor: pointer; font-family: inherit; }
  main { flex: 1; display: grid; grid-template-columns: 300px 1fr; min-height: 0; }
  main.hidden { display: none; }
  aside { border-right: 1px solid var(--border); background: var(--surface); overflow-y: auto; padding: 1rem; display: flex; flex-direction: column; gap: 1.1rem; }
  .eyebrow { font-size: 0.66rem; font-weight: 650; letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-faint); margin: 0 0 0.5rem; }
  .organ-list { display: flex; flex-direction: column; gap: 0.35rem; }
  .organ-btn { display: flex; align-items: center; gap: 0.55rem; text-align: left; padding: 0.5rem 0.6rem; border-radius: 8px; border: 1px solid var(--border); background: var(--surface-raised); color: var(--text); cursor: pointer; font-family: inherit; }
  .organ-btn[aria-pressed="true"] { border-color: var(--accent-strong); background: var(--accent-soft); }
  .organ-swatch { width: 11px; height: 11px; border-radius: 50%; flex-shrink: 0; }
  .label-group { display: flex; flex-direction: column; flex: 1; min-width: 0; }
  .label-group .name { font-size: 0.82rem; font-weight: 650; }
  .label-group .algo { font-size: 0.68rem; color: var(--text-dim); }
  .source-pill { font-size: 0.62rem; font-weight: 650; padding: 0.12rem 0.4rem; border-radius: 999px; white-space: nowrap; }
  .source-pill.real { background: rgba(79,191,120,0.16); color: var(--ok); }
  .metric-row { display: flex; justify-content: space-between; gap: 0.6rem; padding: 0.28rem 0; border-bottom: 1px solid var(--border); font-size: 0.78rem; }
  .metric-row .v { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
  .validation-line { display: flex; align-items: center; gap: 0.4rem; font-size: 0.76rem; padding: 0.5rem 0.6rem; border-radius: 8px; background: var(--surface-raised); border: 1px solid var(--border); }
  .validation-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .validation-dot.pass { background: var(--ok); }
  .validation-dot.fail { background: var(--warn); }
  .note { font-size: 0.72rem; line-height: 1.45; color: var(--text-dim); margin: 0; }
  .stage { position: relative; background: radial-gradient(ellipse at 50% 38%, color-mix(in srgb, var(--surface-raised) 60%, transparent), var(--bg) 72%); }
  #gl-canvas { display: block; width: 100%; height: 100%; cursor: grab; touch-action: none; }
  .stage-hud { position: absolute; left: 1rem; bottom: 1rem; font-size: 0.7rem; color: var(--text-faint); font-family: var(--font-mono); }
  .icon-btn { position: absolute; top: 1rem; right: 1rem; padding: 0.35rem 0.6rem; border-radius: 7px; border: 1px solid var(--border); background: color-mix(in srgb, var(--surface) 78%, transparent); color: var(--text-dim); font-size: 0.72rem; cursor: pointer; font-family: inherit; }
  .slice-stage { position: relative; display: flex; align-items: center; justify-content: center; background: #000; }
  #slice-canvas { image-rendering: pixelated; cursor: crosshair; box-shadow: 0 0 0 1px rgba(255,255,255,0.06); }
  .slider-row { display: flex; align-items: center; gap: 0.5rem; }
  .slider-row input[type="range"] { flex: 1; accent-color: var(--accent); }
  .preset-row { display: flex; gap: 0.35rem; flex-wrap: wrap; }
  .preset-btn { font-size: 0.7rem; padding: 0.28rem 0.55rem; border-radius: 6px; border: 1px solid var(--border); background: var(--surface-raised); color: var(--text-dim); cursor: pointer; font-family: inherit; }
  .preset-btn[aria-pressed="true"] { border-color: var(--accent-strong); color: var(--text); background: var(--accent-soft); }
  .hu-readout { position: absolute; left: 1rem; top: 1rem; font-family: var(--font-mono); font-size: 0.72rem; color: #dce8f2; background: rgba(0,0,0,0.45); padding: 0.25rem 0.5rem; border-radius: 6px; }
  .anatomy-panel { padding: 1.4rem 1.8rem; overflow-y: auto; max-width: 62rem; }
  .anatomy-panel h2 { font-size: 1.3rem; margin: 0 0 0.3rem; text-transform: capitalize; }
  .anatomy-panel .algo-line { font-size: 0.78rem; color: var(--text-dim); margin: 0 0 1.1rem; }
  .anatomy-panel p { font-size: 0.88rem; line-height: 1.65; color: var(--text); }
  .anatomy-panel .source-box { margin-top: 1.2rem; padding: 0.8rem 1rem; border-radius: 10px; background: var(--surface-raised); border: 1px solid var(--border); font-size: 0.78rem; line-height: 1.55; color: var(--text-dim); }
  .anatomy-panel .source-box b { color: var(--text); }
</style>
<body>
<header>
  <span class="mark"></span>
  <h1>Medical3DReconstruction</h1>
  <span class="spacer"></span>
  <div class="tab-switch">
    <button class="tab-btn" id="tab-btn-3d" aria-selected="true">Reconstrucción 3D</button>
    <button class="tab-btn" id="tab-btn-slices" aria-selected="false">Cortes CT</button>
    <button class="tab-btn" id="tab-btn-anatomy" aria-selected="false">Anatomía</button>
  </div>
  <span class="spacer"></span>
  <button class="icon-btn-flat" id="theme-btn">Tema</button>
</header>

<main id="panel-3d">
  <aside>
    <div>
      <p class="eyebrow">Órgano</p>
      <div class="organ-list" id="organ-list"></div>
    </div>
    <div>
      <p class="eyebrow">Métricas de reconstrucción</p>
      <div id="metrics-panel"></div>
    </div>
    <div>
      <p class="eyebrow">Validación</p>
      <div id="validation-panel"></div>
    </div>
    <div>
      <p class="eyebrow">Fuente de datos</p>
      <p class="note" id="source-note"></p>
      <p class="note" id="caveat-note" style="margin-top:0.5rem"></p>
    </div>
  </aside>
  <div class="stage">
    <canvas id="gl-canvas"></canvas>
    <button class="icon-btn" id="reset-btn">Restablecer vista</button>
    <div class="stage-hud">arrastra para rotar &middot; desplaza para hacer zoom</div>
  </div>
</main>

<main id="panel-slices" class="hidden">
  <aside>
    <div>
      <p class="eyebrow">Órgano</p>
      <div class="organ-list" id="organ-list-slices"></div>
    </div>
    <div>
      <p class="eyebrow">Corte</p>
      <div class="slider-row">
        <input type="range" id="slice-slider" min="0" max="0" value="0">
        <span id="slice-readout" style="font-family:var(--font-mono);font-size:0.74rem;min-width:7rem;text-align:right"></span>
      </div>
    </div>
    <div>
      <p class="eyebrow">Preajuste de ventana</p>
      <div class="preset-row" id="preset-row"></div>
    </div>
    <div>
      <p class="eyebrow">Nivel / ancho de ventana</p>
      <div class="slider-row"><input type="range" id="level-slider" min="0" max="255" value="128"><span id="level-value" style="min-width:3rem;text-align:right;font-size:0.72rem"></span></div>
      <div class="slider-row"><input type="range" id="width-slider" min="1" max="510" value="255"><span id="width-value" style="min-width:3rem;text-align:right;font-size:0.72rem"></span></div>
    </div>
    <p class="note" id="slice-source-note"></p>
  </aside>
  <div class="slice-stage">
    <canvas id="slice-canvas"></canvas>
    <div class="hu-readout" id="hu-readout">&mdash;</div>
  </div>
</main>

<main id="panel-anatomy" class="hidden" style="grid-template-columns: 300px 1fr;">
  <aside>
    <div>
      <p class="eyebrow">Órgano</p>
      <div class="organ-list" id="organ-list-anatomy"></div>
    </div>
  </aside>
  <div class="anatomy-panel">
    <h2 id="anatomy-title"></h2>
    <p class="algo-line" id="anatomy-algo"></p>
    <p id="anatomy-text"></p>
    <div class="source-box">
      <p><b>Fuente de datos:</b> <span id="anatomy-source"></span></p>
      <p style="margin-top:0.5rem"><b>Advertencia / alcance:</b> <span id="anatomy-caveat"></span></p>
    </div>
  </div>
</main>

<script>
  const ORGAN_ORDER = __ORGAN_ORDER_JSON__;
  const ORGAN_META = __ORGAN_META_JSON__;
  const VIEWER_DATA = __VIEWER_DATA_JSON__;

  function decodeB64(b64) {
    const bin = atob(b64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return bytes.buffer;
  }
  function hexToRgb01(hex) {
    const v = parseInt(hex.replace("#", ""), 16);
    return [((v >> 16) & 255) / 255, ((v >> 8) & 255) / 255, (v & 255) / 255];
  }
  function fmt(n, d) { return Number(n).toLocaleString(undefined, {maximumFractionDigits: d, minimumFractionDigits: d}); }

  // ---------- tabs ----------
  const tabBtn3d = document.getElementById("tab-btn-3d");
  const tabBtnSlices = document.getElementById("tab-btn-slices");
  const tabBtnAnatomy = document.getElementById("tab-btn-anatomy");
  const panel3d = document.getElementById("panel-3d");
  const panelSlices = document.getElementById("panel-slices");
  const panelAnatomy = document.getElementById("panel-anatomy");

  function activateTab(which) {
    tabBtn3d.setAttribute("aria-selected", String(which === "3d"));
    tabBtnSlices.setAttribute("aria-selected", String(which === "slices"));
    tabBtnAnatomy.setAttribute("aria-selected", String(which === "anatomy"));
    panel3d.classList.toggle("hidden", which !== "3d");
    panelSlices.classList.toggle("hidden", which !== "slices");
    panelAnatomy.classList.toggle("hidden", which !== "anatomy");
    if (which === "slices") { resizeSliceCanvasDisplay(); drawSlice(); }
  }
  tabBtn3d.addEventListener("click", () => activateTab("3d"));
  tabBtnSlices.addEventListener("click", () => activateTab("slices"));
  tabBtnAnatomy.addEventListener("click", () => activateTab("anatomy"));

  // ---------- theme ----------
  document.getElementById("theme-btn").addEventListener("click", () => {
    const root = document.documentElement;
    const current = root.getAttribute("data-theme") || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    root.setAttribute("data-theme", current === "dark" ? "light" : "dark");
  });

  /* =========================================================
     3D reconstruction viewer
     ========================================================= */
  function decodeMesh(meshData) {
    return {
      positions: new Float32Array(decodeB64(meshData.positions_b64)),
      normals: new Float32Array(decodeB64(meshData.normals_b64)),
      indices: new Uint32Array(decodeB64(meshData.indices_b64)),
      numVertices: meshData.num_vertices,
      numTriangles: meshData.num_triangles,
      center: meshData.center,
    };
  }

  const canvas = document.getElementById("gl-canvas");
  const gl = canvas.getContext("webgl", {antialias: true, alpha: false});

  const VS = `attribute vec3 aPosition; attribute vec3 aNormal;
    uniform mat4 uModelView; uniform mat4 uProjection; uniform mat3 uNormalMatrix;
    varying vec3 vNormal; varying vec3 vViewPos;
    void main() {
      vec4 vp = uModelView * vec4(aPosition, 1.0);
      vViewPos = vp.xyz;
      vNormal = normalize(uNormalMatrix * aNormal);
      gl_Position = uProjection * vp;
    }`;
  const FS = `precision highp float; varying vec3 vNormal; varying vec3 vViewPos; uniform vec3 uColor;
    void main() {
      vec3 N = normalize(vNormal); if (!gl_FrontFacing) N = -N;
      vec3 V = normalize(-vViewPos);
      vec3 keyDir = normalize(vec3(0.55, 0.65, 0.85));
      vec3 fillDir = normalize(vec3(-0.6, -0.2, 0.5));
      float key = max(dot(N, keyDir), 0.0);
      float fill = max(dot(N, fillDir), 0.0);
      vec3 halfV = normalize(keyDir + V);
      float spec = pow(max(dot(N, halfV), 0.0), 28.0) * 0.22;
      vec3 color = uColor * (0.32 + key * 0.72 + fill * 0.22) + vec3(spec);
      gl_FragColor = vec4(color, 1.0);
    }`;
  function compile(type, src) {
    const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
    return s;
  }
  const program = gl.createProgram();
  gl.attachShader(program, compile(gl.VERTEX_SHADER, VS));
  gl.attachShader(program, compile(gl.FRAGMENT_SHADER, FS));
  gl.linkProgram(program);
  gl.useProgram(program);
  const aPosition = gl.getAttribLocation(program, "aPosition");
  const aNormal = gl.getAttribLocation(program, "aNormal");
  const uModelView = gl.getUniformLocation(program, "uModelView");
  const uProjection = gl.getUniformLocation(program, "uProjection");
  const uNormalMatrix = gl.getUniformLocation(program, "uNormalMatrix");
  const uColor = gl.getUniformLocation(program, "uColor");
  const posBuf = gl.createBuffer(), normBuf = gl.createBuffer(), idxBuf = gl.createBuffer();
  gl.enable(gl.DEPTH_TEST); gl.enable(gl.CULL_FACE); gl.cullFace(gl.BACK);
  gl.getExtension("OES_element_index_uint");

  function perspective(fovy, aspect, near, far) {
    const f = 1 / Math.tan(fovy / 2), nf = 1 / (near - far);
    return new Float32Array([f/aspect,0,0,0, 0,f,0,0, 0,0,(far+near)*nf,-1, 0,0,2*far*near*nf,0]);
  }
  function lookAt(eye, target, up) {
    let zx=eye[0]-target[0], zy=eye[1]-target[1], zz=eye[2]-target[2];
    let zl=Math.hypot(zx,zy,zz)||1; zx/=zl; zy/=zl; zz/=zl;
    let xx=up[1]*zz-up[2]*zy, xy=up[2]*zx-up[0]*zz, xz=up[0]*zy-up[1]*zx;
    let xl=Math.hypot(xx,xy,xz)||1; xx/=xl; xy/=xl; xz/=xl;
    const yx=zy*xz-zz*xy, yy=zz*xx-zx*xz, yz=zx*xy-zy*xx;
    return new Float32Array([xx,yx,zx,0, xy,yy,zy,0, xz,yz,zz,0,
      -(xx*eye[0]+xy*eye[1]+xz*eye[2]), -(yx*eye[0]+yy*eye[1]+yz*eye[2]), -(zx*eye[0]+zy*eye[1]+zz*eye[2]), 1]);
  }
  function normalMat3(m) { return new Float32Array([m[0],m[1],m[2], m[4],m[5],m[6], m[8],m[9],m[10]]); }

  let currentMesh = null, currentColor = [0.7,0.7,0.7], boundingRadius = 1;
  let theta = 0.6, phi = 1.15, radius = 1, targetRadius = 1;
  let reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let autoRotate = !reduceMotion;
  let dragging = false, lastX = 0, lastY = 0;

  function frameCamera(mesh) {
    boundingRadius = 1;
    const c = mesh.center;
    for (let i = 0; i < mesh.positions.length; i += 3) {
      const d = Math.hypot(mesh.positions[i]-c[0], mesh.positions[i+1]-c[1], mesh.positions[i+2]-c[2]);
      if (d > boundingRadius) boundingRadius = d;
    }
    radius = boundingRadius * 2.6; targetRadius = radius;
  }
  function uploadMesh(mesh) {
    gl.bindBuffer(gl.ARRAY_BUFFER, posBuf); gl.bufferData(gl.ARRAY_BUFFER, mesh.positions, gl.STATIC_DRAW);
    gl.bindBuffer(gl.ARRAY_BUFFER, normBuf); gl.bufferData(gl.ARRAY_BUFFER, mesh.normals, gl.STATIC_DRAW);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, idxBuf); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, mesh.indices, gl.STATIC_DRAW);
  }

  canvas.addEventListener("pointerdown", e => { dragging = true; autoRotate = false; lastX = e.clientX; lastY = e.clientY; canvas.setPointerCapture(e.pointerId); });
  canvas.addEventListener("pointerup", () => dragging = false);
  canvas.addEventListener("pointermove", e => {
    if (!dragging) return;
    theta -= (e.clientX - lastX) * 0.008; phi -= (e.clientY - lastY) * 0.008;
    phi = Math.max(0.15, Math.min(Math.PI - 0.15, phi));
    lastX = e.clientX; lastY = e.clientY;
  });
  canvas.addEventListener("wheel", e => {
    e.preventDefault();
    targetRadius = Math.max(boundingRadius*1.15, Math.min(boundingRadius*6, targetRadius * Math.pow(1.0012, e.deltaY)));
  }, {passive: false});
  document.getElementById("reset-btn").addEventListener("click", () => {
    const meta = ORGAN_META[currentOrganKey];
    theta = meta.initial_theta; phi = meta.initial_phi; targetRadius = boundingRadius * 2.6;
    autoRotate = !reduceMotion;
  });

  function resizeGl() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.round(canvas.clientWidth * dpr), h = Math.round(canvas.clientHeight * dpr);
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
  }
  function render3d() {
    resizeGl();
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.clearColor(0.039, 0.055, 0.075, 1.0);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    if (currentMesh) {
      radius += (targetRadius - radius) * 0.12;
      if (autoRotate) theta += 0.0022;
      const c = currentMesh.center;
      const eye = [c[0]+radius*Math.sin(phi)*Math.sin(theta), c[1]+radius*Math.cos(phi), c[2]+radius*Math.sin(phi)*Math.cos(theta)];
      const view = lookAt(eye, c, [0,1,0]);
      const proj = perspective(Math.PI/4.2, canvas.width/Math.max(1,canvas.height), Math.max(0.01,boundingRadius*0.02), boundingRadius*20);
      gl.useProgram(program);
      gl.uniformMatrix4fv(uModelView, false, view);
      gl.uniformMatrix4fv(uProjection, false, proj);
      gl.uniformMatrix3fv(uNormalMatrix, false, normalMat3(view));
      gl.uniform3fv(uColor, currentColor);
      gl.bindBuffer(gl.ARRAY_BUFFER, posBuf); gl.enableVertexAttribArray(aPosition); gl.vertexAttribPointer(aPosition, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, normBuf); gl.enableVertexAttribArray(aNormal); gl.vertexAttribPointer(aNormal, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, idxBuf);
      gl.drawElements(gl.TRIANGLES, currentMesh.indices.length, gl.UNSIGNED_INT, 0);
    }
    requestAnimationFrame(render3d);
  }

  // ---------- shared panels ----------
  const metricsPanelEl = document.getElementById("metrics-panel");
  const validationPanelEl = document.getElementById("validation-panel");
  const sourceNoteEl = document.getElementById("source-note");
  const caveatNoteEl = document.getElementById("caveat-note");

  function renderMetrics(metrics) {
    const rows = [
      ["Volumen", fmt(metrics.volume_ml, 1) + " mL"],
      ["Área de superficie", fmt(metrics.surface_area_mm2, 0) + " mm²"],
      ["Centroide (mm)", metrics.centroid_mm.map((v) => fmt(v, 0)).join(", ")],
      ["Bounding box mín.", metrics.bounding_box_min_mm.map((v) => fmt(v, 0)).join(", ")],
      ["Bounding box máx.", metrics.bounding_box_max_mm.map((v) => fmt(v, 0)).join(", ")],
      ["Vértices", fmt(metrics.num_vertices, 0)],
      ["Triángulos", fmt(metrics.num_triangles, 0)],
    ];
    metricsPanelEl.innerHTML = rows.map(([k, v]) => `<div class="metric-row"><span class="k">${k}</span><span class="v">${v}</span></div>`).join("")
      + `<p class="note" style="margin-top:0.5rem">Estas cifras describen la malla STL/OBJ/PLY exportada. La vista 3D está decimada para una interacción fluida — misma forma, menos triángulos.</p>`;
  }
  function renderValidation(validation) {
    const cls = validation.passed ? "pass" : "fail";
    const label = validation.passed ? "Aprobado — malla estanca, volumen plausible" : "Marcado — ver advertencias";
    validationPanelEl.innerHTML = `<div class="validation-line"><span class="validation-dot ${cls}"></span><span>${label}</span></div>`;
  }

  function organListHtml(activeKey) {
    return ORGAN_ORDER.map((key) => {
      const meta = ORGAN_META[key];
      return `
        <button class="organ-btn" data-organ="${key}" role="tab" aria-pressed="${key === activeKey}">
          <span class="organ-swatch" style="background:${meta.color_hex}"></span>
          <span class="label-group"><span class="name">${meta.label}</span><span class="algo">${meta.algo}</span></span>
          <span class="source-pill real">datos reales</span>
        </button>`;
    }).join("");
  }

  let currentOrganKey = ORGAN_ORDER[0];

  function selectOrgan(key) {
    currentOrganKey = key;
    const data = VIEWER_DATA[key];
    const meta = ORGAN_META[key];

    const mesh = decodeMesh(data.mesh);
    currentMesh = mesh;
    currentColor = hexToRgb01(meta.color_hex);
    theta = meta.initial_theta; phi = meta.initial_phi;
    frameCamera(mesh);
    uploadMesh(mesh);
    autoRotate = !reduceMotion;

    renderMetrics(data.metrics);
    renderValidation(data.validation);
    sourceNoteEl.textContent = meta.source_note;
    caveatNoteEl.textContent = meta.caveat;

    document.getElementById("anatomy-title").textContent = meta.label;
    document.getElementById("anatomy-algo").textContent = meta.algo;
    document.getElementById("anatomy-text").textContent = meta.anatomy;
    document.getElementById("anatomy-source").textContent = meta.source_note;
    document.getElementById("anatomy-caveat").textContent = meta.caveat;

    document.getElementById("slice-source-note").textContent =
      "Cortes del volumen preprocesado real que este pipeline realmente segmentó para " + meta.label.toLowerCase() +
      " (mismos datos de origen que la reconstrucción 3D), submuestreado para un archivo más ligero.";

    for (const list of [document.getElementById("organ-list"), document.getElementById("organ-list-slices"), document.getElementById("organ-list-anatomy")]) {
      for (const btn of list.querySelectorAll(".organ-btn")) {
        btn.setAttribute("aria-pressed", String(btn.dataset.organ === key));
      }
    }

    loadSliceVolume(data.slices);
    if (!panelSlices.classList.contains("hidden")) { resizeSliceCanvasDisplay(); drawSlice(); }
  }

  for (const listId of ["organ-list", "organ-list-slices", "organ-list-anatomy"]) {
    document.getElementById(listId).innerHTML = organListHtml(ORGAN_ORDER[0]);
  }
  for (const listId of ["organ-list", "organ-list-slices", "organ-list-anatomy"]) {
    for (const btn of document.getElementById(listId).querySelectorAll(".organ-btn")) {
      btn.addEventListener("click", () => selectOrgan(btn.dataset.organ));
    }
  }

  /* =========================================================
     CT / slice viewer (per organ)
     ========================================================= */
  let sv = null; // active slice volume
  const sliceSlider = document.getElementById("slice-slider");
  const sliceReadout = document.getElementById("slice-readout");
  const levelSlider = document.getElementById("level-slider");
  const widthSlider = document.getElementById("width-slider");
  const levelValueEl = document.getElementById("level-value");
  const widthValueEl = document.getElementById("width-value");
  const presetRowEl = document.getElementById("preset-row");
  const sliceCanvas = document.getElementById("slice-canvas");
  const sliceCtx = sliceCanvas.getContext("2d");
  const huReadoutEl = document.getElementById("hu-readout");

  let windowLevel = 128, windowWidth = 255;
  const PRESETS = [
    {label: "Bajo", level: 64, width: 128},
    {label: "Medio", level: 128, width: 255},
    {label: "Alto contraste", level: 128, width: 60},
    {label: "Rango completo", level: 128, width: 510},
  ];
  presetRowEl.innerHTML = PRESETS.map((p, i) => `<button class="preset-btn" data-i="${i}" aria-pressed="${i===1}">${p.label}</button>`).join("");
  for (const btn of presetRowEl.querySelectorAll(".preset-btn")) {
    btn.addEventListener("click", () => {
      const p = PRESETS[Number(btn.dataset.i)];
      windowLevel = p.level; windowWidth = p.width;
      levelSlider.value = windowLevel; widthSlider.value = windowWidth;
      levelValueEl.textContent = windowLevel; widthValueEl.textContent = windowWidth;
      for (const b of presetRowEl.querySelectorAll(".preset-btn")) b.setAttribute("aria-pressed", String(b === btn));
      drawSlice();
    });
  }
  levelSlider.value = windowLevel; widthSlider.value = windowWidth;
  levelValueEl.textContent = windowLevel; widthValueEl.textContent = windowWidth;
  function clearPresets() { for (const b of presetRowEl.querySelectorAll(".preset-btn")) b.setAttribute("aria-pressed", "false"); }
  levelSlider.addEventListener("input", () => { windowLevel = Number(levelSlider.value); levelValueEl.textContent = windowLevel; clearPresets(); drawSlice(); });
  widthSlider.addEventListener("input", () => { windowWidth = Math.max(1, Number(widthSlider.value)); widthValueEl.textContent = windowWidth; clearPresets(); drawSlice(); });
  sliceSlider.addEventListener("input", drawSlice);

  let imgData = null;

  function loadSliceVolume(slicesData) {
    sv = {
      voxels: new Uint8Array(decodeB64(slicesData.voxels_b64)),
      shape: slicesData.shape_zyx,
      spacing: slicesData.spacing_xyz,
      origin: slicesData.origin_xyz,
      valueMin: slicesData.value_min,
      valueMax: slicesData.value_max,
    };
    const [snz, sny, snx] = sv.shape;
    sliceSlider.max = String(snz - 1);
    sliceSlider.value = String(Math.floor(snz / 2));
    sliceCanvas.width = snx; sliceCanvas.height = sny;
    imgData = sliceCtx.createImageData(snx, sny);
  }

  function drawSlice() {
    if (!sv) return;
    const [snz, sny, snx] = sv.shape;
    const z = Math.min(Number(sliceSlider.value), snz - 1);
    const zMm = (sv.origin[2] + z * sv.spacing[2]).toFixed(1);
    sliceReadout.textContent = `${z+1} / ${snz} · z=${zMm}mm`;
    const off = z * sny * snx;
    const lo = windowLevel - windowWidth/2, scale = 255/windowWidth;
    const data = imgData.data;
    for (let i = 0; i < sny*snx; i++) {
      let val = (sv.voxels[off+i] - lo) * scale;
      val = val < 0 ? 0 : val > 255 ? 255 : val;
      const o = i*4; data[o]=val; data[o+1]=val; data[o+2]=val; data[o+3]=255;
    }
    sliceCtx.putImageData(imgData, 0, 0);
  }
  function resizeSliceCanvasDisplay() {
    if (!sv) return;
    const [, sny, snx] = sv.shape;
    const stage = sliceCanvas.parentElement;
    const availW = stage.clientWidth * 0.92, availH = stage.clientHeight * 0.92;
    const aspect = snx / sny;
    let w = availW, h = w / aspect;
    if (h > availH) { h = availH; w = h * aspect; }
    sliceCanvas.style.width = Math.round(w) + "px";
    sliceCanvas.style.height = Math.round(h) + "px";
  }
  window.addEventListener("resize", () => { if (!panelSlices.classList.contains("hidden")) resizeSliceCanvasDisplay(); });
  sliceCanvas.addEventListener("mousemove", (e) => {
    if (!sv) return;
    const [, sny, snx] = sv.shape;
    const rect = sliceCanvas.getBoundingClientRect();
    const px = Math.floor((e.clientX-rect.left)/rect.width*snx), py = Math.floor((e.clientY-rect.top)/rect.height*sny);
    if (px<0||py<0||px>=snx||py>=sny) return;
    const z = Math.min(Number(sliceSlider.value), sv.shape[0]-1);
    const raw = sv.voxels[z*sny*snx+py*snx+px];
    const orig = sv.valueMin + (raw/255)*(sv.valueMax - sv.valueMin);
    huReadoutEl.textContent = `(${px}, ${py})  ${raw}/255  ≈${orig.toFixed(0)}`;
  });
  sliceCanvas.addEventListener("mouseleave", () => { huReadoutEl.textContent = "—"; });

  // ---------- boot ----------
  selectOrgan(ORGAN_ORDER[0]);
  requestAnimationFrame(render3d);
</script>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", required=True, help="Path to the JSON payload from build_demo_payload.py")
    parser.add_argument("--output", required=True, help="Path to write the final HTML artifact to")
    args = parser.parse_args()

    with open(args.payload) as f:
        payload = json.load(f)

    html = build(payload)
    os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        f.write(html)

    size_mb = os.path.getsize(args.output) / (1024 * 1024)
    print(f"Wrote {args.output} ({size_mb:.2f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
