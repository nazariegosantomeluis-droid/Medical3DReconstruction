"""Standalone interactive HTML export: a 3D mesh viewer + CT slice scrubber
for a single pipeline run, viewable in any browser with no server, no
install, and no external dependencies (a self-contained WebGL renderer,
no CDN scripts).

This is a presentation layer over data the pipeline already computed
(the mesh and the source volume) — it does not add new segmentation or
analysis capability, so it does not expand the project's scope beyond
"visualize the reconstruction."
"""

from __future__ import annotations

import base64
import json
import os

import numpy as np
import trimesh

from medical3d.core.mesh import MeshMetrics
from medical3d.core.mesh_ops import decimate_mesh
from medical3d.core.validation import ValidationReport
from medical3d.core.volume import Volume

_MAX_PREVIEW_FACES = 40000
_MAX_SLICE_EDGE_PX = 200

ORGAN_COLORS = {
    "lungs": "#e8b4b8",
    "heart": "#c0392b",
    "liver": "#b9793f",
    "kidneys": "#a8447a",
}


def _pack_mesh(mesh: trimesh.Trimesh) -> dict:
    if len(mesh.faces) > _MAX_PREVIEW_FACES:
        mesh = decimate_mesh(mesh, target_face_fraction=_MAX_PREVIEW_FACES / len(mesh.faces))
    mesh = mesh.copy()
    mesh.fix_normals()
    verts = mesh.vertices.astype(np.float32)
    norms = mesh.vertex_normals.astype(np.float32)
    faces = mesh.faces.astype(np.uint32)
    return {
        "positions_b64": base64.b64encode(verts.tobytes()).decode("ascii"),
        "normals_b64": base64.b64encode(norms.tobytes()).decode("ascii"),
        "indices_b64": base64.b64encode(faces.tobytes()).decode("ascii"),
        "center": verts.mean(axis=0).tolist(),
    }


def _pack_slices(volume: Volume, max_edge_px: int = _MAX_SLICE_EDGE_PX) -> dict:
    nz, ny, nx = volume.array.shape
    stride_y = max(1, round(ny / max_edge_px))
    stride_x = max(1, round(nx / max_edge_px))
    small = volume.array[:, ::stride_y, ::stride_x].astype(np.int16)

    sx, sy, sz = volume.spacing
    return {
        "shape_zyx": list(small.shape),
        "spacing_xyz": [sx * stride_x, sy * stride_y, sz],
        "origin_xyz": list(volume.origin),
        "hu_min": int(small.min()),
        "hu_max": int(small.max()),
        "voxels_b64": base64.b64encode(small.tobytes()).decode("ascii"),
    }


def export_interactive_viewer(
    organ: str,
    mesh: trimesh.Trimesh,
    metrics: MeshMetrics,
    validation: ValidationReport,
    volume: Volume,
    output_path: str,
) -> str:
    """Write a self-contained HTML file with a rotatable 3D view of ``mesh``
    and a windowed CT slice scrubber over ``volume``.

    Returns the path written to.
    """
    payload = {
        "organ": organ,
        "color": ORGAN_COLORS.get(organ.lower(), "#c0c0c0"),
        "mesh": _pack_mesh(mesh),
        "metrics": metrics.as_dict(),
        "validation": validation.as_dict(),
        "slices": _pack_slices(volume),
    }

    html = _HTML_TEMPLATE.replace("__PAYLOAD_JSON__", json.dumps(payload))

    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)
    return output_path


_HTML_TEMPLATE = r"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Visor Medical3DReconstruction</title>
<style>
  :root {
    --bg: #0a0e13; --surface: #121820; --surface-raised: #1a222c; --border: #26313d;
    --text: #eaf0f6; --text-dim: #7e93a7; --text-faint: #4b5c6c;
    --accent: #46c9c2; --accent-soft: rgba(70,201,194,0.14); --accent-strong: #2f918c;
    --ok: #4fbf78; --warn: #d99a3c;
    font-family: -apple-system, "Segoe UI", sans-serif;
  }
  * { box-sizing: border-box; }
  html, body { height: 100%; margin: 0; background: var(--bg); color: var(--text); }
  body { display: flex; flex-direction: column; overflow: hidden; }
  header { display: flex; align-items: center; gap: 0.75rem; padding: 0.7rem 1.1rem; background: var(--surface-raised); border-bottom: 1px solid var(--border); }
  header .mark { width: 9px; height: 9px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
  header h1 { font-size: 0.92rem; margin: 0; }
  header .spacer { flex: 1; }
  .tab-switch { display: flex; gap: 0.2rem; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 0.2rem; }
  .tab-btn { font-size: 0.76rem; font-weight: 600; padding: 0.3rem 0.7rem; border-radius: 6px; border: none; background: transparent; color: var(--text-dim); cursor: pointer; }
  .tab-btn[aria-selected="true"] { background: var(--accent-soft); color: var(--text); }
  main { flex: 1; display: grid; grid-template-columns: 280px 1fr; min-height: 0; }
  main.hidden { display: none; }
  aside { border-right: 1px solid var(--border); background: var(--surface); overflow-y: auto; padding: 1rem; display: flex; flex-direction: column; gap: 1.1rem; }
  .eyebrow { font-size: 0.66rem; font-weight: 650; letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-faint); margin: 0 0 0.5rem; }
  .metric-row { display: flex; justify-content: space-between; gap: 0.6rem; padding: 0.28rem 0; border-bottom: 1px solid var(--border); font-size: 0.78rem; }
  .metric-row .v { font-family: ui-monospace, monospace; font-variant-numeric: tabular-nums; }
  .validation-line { display: flex; align-items: center; gap: 0.4rem; font-size: 0.76rem; padding: 0.5rem 0.6rem; border-radius: 8px; background: var(--surface-raised); border: 1px solid var(--border); }
  .validation-dot { width: 8px; height: 8px; border-radius: 50%; }
  .validation-dot.pass { background: var(--ok); }
  .validation-dot.fail { background: var(--warn); }
  .stage { position: relative; background: radial-gradient(ellipse at 50% 38%, color-mix(in srgb, var(--surface-raised) 60%, transparent), var(--bg) 72%); }
  #gl-canvas { display: block; width: 100%; height: 100%; cursor: grab; touch-action: none; }
  .stage-hud { position: absolute; left: 1rem; bottom: 1rem; font-size: 0.7rem; color: var(--text-faint); font-family: ui-monospace, monospace; }
  .icon-btn { position: absolute; top: 1rem; right: 1rem; padding: 0.35rem 0.6rem; border-radius: 7px; border: 1px solid var(--border); background: color-mix(in srgb, var(--surface) 78%, transparent); color: var(--text-dim); font-size: 0.72rem; cursor: pointer; }
  .slice-stage { position: relative; display: flex; align-items: center; justify-content: center; background: #000; }
  #slice-canvas { image-rendering: pixelated; cursor: crosshair; box-shadow: 0 0 0 1px rgba(255,255,255,0.06); }
  .slider-row { display: flex; align-items: center; gap: 0.5rem; }
  .slider-row input[type="range"] { flex: 1; accent-color: var(--accent); }
  .preset-row { display: flex; gap: 0.35rem; flex-wrap: wrap; }
  .preset-btn { font-size: 0.7rem; padding: 0.28rem 0.55rem; border-radius: 6px; border: 1px solid var(--border); background: var(--surface-raised); color: var(--text-dim); cursor: pointer; }
  .preset-btn[aria-pressed="true"] { border-color: var(--accent-strong); color: var(--text); background: var(--accent-soft); }
  .hu-readout { position: absolute; left: 1rem; top: 1rem; font-family: ui-monospace, monospace; font-size: 0.72rem; color: #dce8f2; background: rgba(0,0,0,0.45); padding: 0.25rem 0.5rem; border-radius: 6px; }
  .note { font-size: 0.72rem; line-height: 1.4; color: var(--text-dim); }
</style>
</head>
<body>
<header>
  <span class="mark"></span>
  <h1>Medical3DReconstruction</h1>
  <span class="spacer"></span>
  <div class="tab-switch">
    <button class="tab-btn" id="tab-3d" aria-selected="true">Reconstrucción 3D</button>
    <button class="tab-btn" id="tab-slices" aria-selected="false">Visor de cortes CT</button>
  </div>
</header>

<main id="panel-3d">
  <aside>
    <div>
      <p class="eyebrow">Órgano</p>
      <p style="font-size:1rem;font-weight:650;text-transform:capitalize" id="organ-name"></p>
    </div>
    <div>
      <p class="eyebrow">Métricas de reconstrucción</p>
      <div id="metrics-panel"></div>
    </div>
    <div>
      <p class="eyebrow">Validación</p>
      <div id="validation-panel"></div>
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
      <p class="eyebrow">Corte</p>
      <div class="slider-row">
        <input type="range" id="slice-slider" min="0" max="0" value="0">
        <span id="slice-readout" style="font-family:ui-monospace,monospace;font-size:0.74rem;min-width:6rem;text-align:right"></span>
      </div>
    </div>
    <div>
      <p class="eyebrow">Preajuste de ventana</p>
      <div class="preset-row" id="preset-row"></div>
    </div>
    <div>
      <p class="eyebrow">Nivel / ancho de ventana (HU)</p>
      <div class="slider-row"><input type="range" id="level-slider" min="-1024" max="2000" value="40"><span id="level-value" style="min-width:3rem;text-align:right;font-size:0.72rem"></span></div>
      <div class="slider-row"><input type="range" id="width-slider" min="1" max="4000" value="400"><span id="width-value" style="min-width:3rem;text-align:right;font-size:0.72rem"></span></div>
    </div>
    <p class="note">Escaneo original, sin segmentación aplicada — submuestreado en el plano para un archivo más ligero.</p>
  </aside>
  <div class="slice-stage">
    <canvas id="slice-canvas"></canvas>
    <div class="hu-readout" id="hu-readout">&mdash;</div>
  </div>
</main>

<script>
  const PAYLOAD = __PAYLOAD_JSON__;

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

  // ---- tabs ----
  const tab3d = document.getElementById("tab-3d"), tabSlices = document.getElementById("tab-slices");
  const panel3d = document.getElementById("panel-3d"), panelSlices = document.getElementById("panel-slices");
  function activateTab(which) {
    const is3d = which === "3d";
    tab3d.setAttribute("aria-selected", String(is3d));
    tabSlices.setAttribute("aria-selected", String(!is3d));
    panel3d.classList.toggle("hidden", !is3d);
    panelSlices.classList.toggle("hidden", is3d);
    if (!is3d) { resizeSliceDisplay(); drawSlice(); }
  }
  tab3d.addEventListener("click", () => activateTab("3d"));
  tabSlices.addEventListener("click", () => activateTab("slices"));

  // ---- 3D viewer ----
  document.getElementById("organ-name").textContent = PAYLOAD.organ;
  const metricsPanel = document.getElementById("metrics-panel");
  const m = PAYLOAD.metrics;
  metricsPanel.innerHTML = [
    ["Volumen", fmt(m.volume_ml, 1) + " mL"],
    ["Área de superficie", fmt(m.surface_area_mm2, 0) + " mm²"],
    ["Centroide (mm)", m.centroid_mm.map(v => fmt(v, 0)).join(", ")],
    ["Bounding box mín.", m.bounding_box_min_mm.map(v => fmt(v, 0)).join(", ")],
    ["Bounding box máx.", m.bounding_box_max_mm.map(v => fmt(v, 0)).join(", ")],
    ["Vértices", fmt(m.num_vertices, 0)],
    ["Triángulos", fmt(m.num_triangles, 0)],
  ].map(([k, v]) => `<div class="metric-row"><span>${k}</span><span class="v">${v}</span></div>`).join("");

  const v = PAYLOAD.validation;
  document.getElementById("validation-panel").innerHTML = `
    <div class="validation-line">
      <span class="validation-dot ${v.passed ? "pass" : "fail"}"></span>
      <span>${v.passed ? "Aprobado — malla estanca, volumen plausible" : "Marcado — ver advertencias"}</span>
    </div>`;

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

  const positions = new Float32Array(decodeB64(PAYLOAD.mesh.positions_b64));
  const normals = new Float32Array(decodeB64(PAYLOAD.mesh.normals_b64));
  const indices = new Uint32Array(decodeB64(PAYLOAD.mesh.indices_b64));
  const center = PAYLOAD.mesh.center;
  const color = hexToRgb01(PAYLOAD.color);

  let boundingRadius = 1;
  for (let i = 0; i < positions.length; i += 3) {
    const d = Math.hypot(positions[i]-center[0], positions[i+1]-center[1], positions[i+2]-center[2]);
    if (d > boundingRadius) boundingRadius = d;
  }

  gl.bindBuffer(gl.ARRAY_BUFFER, posBuf); gl.bufferData(gl.ARRAY_BUFFER, positions, gl.STATIC_DRAW);
  gl.bindBuffer(gl.ARRAY_BUFFER, normBuf); gl.bufferData(gl.ARRAY_BUFFER, normals, gl.STATIC_DRAW);
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, idxBuf); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, indices, gl.STATIC_DRAW);

  let theta = 0.6, phi = 1.15, radius = boundingRadius * 2.6, targetRadius = radius;
  let autoRotate = !matchMedia("(prefers-reduced-motion: reduce)").matches;
  let dragging = false, lastX = 0, lastY = 0;

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
    theta = 0.6; phi = 1.15; targetRadius = boundingRadius * 2.6; autoRotate = !matchMedia("(prefers-reduced-motion: reduce)").matches;
  });

  function resizeGl() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.round(canvas.clientWidth * dpr), h = Math.round(canvas.clientHeight * dpr);
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
  }

  function render() {
    resizeGl();
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.clearColor(0.039, 0.055, 0.075, 1.0);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    radius += (targetRadius - radius) * 0.12;
    if (autoRotate) theta += 0.0022;
    const eye = [center[0]+radius*Math.sin(phi)*Math.sin(theta), center[1]+radius*Math.cos(phi), center[2]+radius*Math.sin(phi)*Math.cos(theta)];
    const view = lookAt(eye, center, [0,1,0]);
    const proj = perspective(Math.PI/4.2, canvas.width/canvas.height, boundingRadius*0.02, boundingRadius*20);
    gl.useProgram(program);
    gl.uniformMatrix4fv(uModelView, false, view);
    gl.uniformMatrix4fv(uProjection, false, proj);
    gl.uniformMatrix3fv(uNormalMatrix, false, normalMat3(view));
    gl.uniform3fv(uColor, color);
    gl.bindBuffer(gl.ARRAY_BUFFER, posBuf); gl.enableVertexAttribArray(aPosition); gl.vertexAttribPointer(aPosition, 3, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ARRAY_BUFFER, normBuf); gl.enableVertexAttribArray(aNormal); gl.vertexAttribPointer(aNormal, 3, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, idxBuf);
    gl.drawElements(gl.TRIANGLES, indices.length, gl.UNSIGNED_INT, 0);
    requestAnimationFrame(render);
  }
  requestAnimationFrame(render);

  // ---- slice viewer ----
  const sv = {
    voxels: new Int16Array(decodeB64(PAYLOAD.slices.voxels_b64)),
    shape: PAYLOAD.slices.shape_zyx,
    spacing: PAYLOAD.slices.spacing_xyz,
    origin: PAYLOAD.slices.origin_xyz,
    huMin: PAYLOAD.slices.hu_min,
    huMax: PAYLOAD.slices.hu_max,
  };
  const [snz, sny, snx] = sv.shape;
  const sliceSlider = document.getElementById("slice-slider");
  const sliceReadout = document.getElementById("slice-readout");
  const sliceCanvas = document.getElementById("slice-canvas");
  const sliceCtx = sliceCanvas.getContext("2d");
  const huReadout = document.getElementById("hu-readout");
  const levelSlider = document.getElementById("level-slider"), widthSlider = document.getElementById("width-slider");
  const levelValue = document.getElementById("level-value"), widthValue = document.getElementById("width-value");
  const presetRow = document.getElementById("preset-row");

  sliceSlider.max = String(snz - 1);
  sliceSlider.value = String(Math.floor(snz / 2));
  sliceCanvas.width = snx; sliceCanvas.height = sny;

  const PRESETS = [
    {label: "Pulmón", level: -600, width: 1500},
    {label: "Tejido blando", level: 40, width: 400},
    {label: "Hueso", level: 400, width: 1800},
    {label: "Rango completo", level: Math.round((sv.huMin+sv.huMax)/2), width: sv.huMax - sv.huMin},
  ];
  let windowLevel = 40, windowWidth = 400;
  presetRow.innerHTML = PRESETS.map((p, i) => `<button class="preset-btn" data-i="${i}" aria-pressed="${i===1}">${p.label}</button>`).join("");
  for (const btn of presetRow.querySelectorAll(".preset-btn")) {
    btn.addEventListener("click", () => {
      const p = PRESETS[Number(btn.dataset.i)];
      windowLevel = p.level; windowWidth = p.width;
      levelSlider.value = windowLevel; widthSlider.value = windowWidth;
      levelValue.textContent = windowLevel; widthValue.textContent = windowWidth;
      for (const b of presetRow.querySelectorAll(".preset-btn")) b.setAttribute("aria-pressed", String(b === btn));
      drawSlice();
    });
  }
  levelSlider.value = windowLevel; widthSlider.value = windowWidth;
  levelValue.textContent = windowLevel; widthValue.textContent = windowWidth;
  levelSlider.addEventListener("input", () => { windowLevel = Number(levelSlider.value); levelValue.textContent = windowLevel; clearPresets(); drawSlice(); });
  widthSlider.addEventListener("input", () => { windowWidth = Math.max(1, Number(widthSlider.value)); widthValue.textContent = windowWidth; clearPresets(); drawSlice(); });
  function clearPresets() { for (const b of presetRow.querySelectorAll(".preset-btn")) b.setAttribute("aria-pressed", "false"); }
  sliceSlider.addEventListener("input", drawSlice);

  const imgData = sliceCtx.createImageData(snx, sny);
  function drawSlice() {
    const z = Number(sliceSlider.value);
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
  function resizeSliceDisplay() {
    const stage = sliceCanvas.parentElement;
    const availW = stage.clientWidth * 0.92, availH = stage.clientHeight * 0.92;
    const aspect = snx / sny;
    let w = availW, h = w / aspect;
    if (h > availH) { h = availH; w = h * aspect; }
    sliceCanvas.style.width = Math.round(w) + "px";
    sliceCanvas.style.height = Math.round(h) + "px";
  }
  window.addEventListener("resize", () => { if (!panelSlices.classList.contains("hidden")) resizeSliceDisplay(); });
  sliceCanvas.addEventListener("mousemove", e => {
    const rect = sliceCanvas.getBoundingClientRect();
    const px = Math.floor((e.clientX-rect.left)/rect.width*snx), py = Math.floor((e.clientY-rect.top)/rect.height*sny);
    if (px<0||py<0||px>=snx||py>=sny) return;
    const z = Number(sliceSlider.value);
    huReadout.textContent = `(${px}, ${py})  ${sv.voxels[z*sny*snx+py*snx+px]} HU`;
  });
  sliceCanvas.addEventListener("mouseleave", () => huReadout.textContent = "—");
</script>
</body>
</html>
"""
