"""
Arma corazon-segmentado.glb a partir del set BodyParts3D 4.3.

Corre esto DESPUES de:
    git clone https://github.com/olivercase/body_parts_3d_api.git
    cd body_parts_3d_api
    git lfs install
    git lfs pull --include="<pega aqui el contenido de lfs_include_pattern.txt>"
    pip install trimesh numpy scipy networkx
    python3 build_corazon_segmentado.py

No requiere Blender ni ningun editor 3D: solo junta mallas .obj ya
existentes en un unico .glb, coloreando cada estructura y nombrando cada
nodo exactamente como lo espera anatomy-viewer-react/src/data/estructuras.json.

Datos (c) Database Center for Life Science (DBCLS) - BodyParts3D/Anatomography,
licencia CC BY-SA 2.1 Japan. Si publicas este .glb, debes mantener esa
atribucion y licencia para el modelo (el codigo del visor puede seguir
teniendo su propia licencia, pero el modelo en si es CC BY-SA).
"""

import csv
import glob
import os
import re

import numpy as np
import trimesh
from trimesh.smoothing import laplacian_calculation

MANIFEST = "MANIFEST.csv"
MESHES_DIR = "meshes"
OUTPUT = "corazon-segmentado.glb"

# id de estructura -> lista de regex (case-insensitive) sobre la columna
# "name" de MANIFEST.csv. Cualquier fila que matchee CUALQUIER regex de la
# lista entra en el grupo de esa estructura y se fusiona en una sola malla.
GROUPS = {
    "venas_cavas": [r"^(superior|inferior) vena cava$"],
    "aorta": [r"^(ascending aorta|arch of aorta|descending aorta)$"],
    "arterias_pulmonares": [r"^trunk of (left|right) pulmonary artery$"],
    "venas_pulmonares": [r"^trunk of (left|right) (superior|inferior) pulmonary vein$"],
    "auricula_derecha": [r"^wall of right atrium$"],
    "auricula_izquierda": [r"^wall of left atrium$"],
    "ventriculo_derecho": [r"^cavity of right ventricle$"],
    "ventriculo_izquierdo": [r"^cavity of left ventricle$"],
    "valvula_aortica": [r"cusp of aortic valve$"],
    "valvula_pulmonar": [r"cusp of pulmonary valve$"],
    "valvula_bicuspide": [r"leaflet of mitral valve$"],
    "valvula_tricuspide": [r"leaflet of tricuspid valve$"],
    "arterias_coronarias": [r"coronary artery$"],
    "venas_coronarias": [r"^(great|middle|small|anterior) cardiac vein$", r"^coronary sinus$"],
    "laringe": [
        r"^thyroid cartilage$",
        r"^cricoid cartilage$",
        r"^(left|right) arytenoid cartilage$",
        r"^epiglottis$",
        r"crico-arytenoid$",
        r"thyro-arytenoid( proper)?$",
        r"^transverse arytenoid$",
        r"^left oblique arytenoid$",
        r"^right oblique arytenoid$",
    ],
    "traquea": [r"^trachea$"],
    "bronquios": [r"^(left|right) main bronchus( proper)?$", r"bronchial tree$"],
    "pulmones": [r"^parenchyma of .* bronchopulmonary segment$"],
}

# Estas 5 no existen como malla individual en BodyParts3D (corazon: se
# arma de sus partes, no hay "Heart" unico; pericardio/nariz: no estan
# modelados en este atlas; bronquiolos/alveolos: son microscopicos, ningun
# atlas macro los modela como malla). Quedan como nodos "solo concepto" en
# estructuras.json, alcanzables por el mapa de conexiones, no por clic 3D.
HUB_ONLY = ["corazon", "pericardio", "nariz", "bronquiolos", "alveolos"]

# Color base por estructura (RGBA 0-255) solo para que el modelo se lea
# visualmente sin depender de materiales del .obj original (BodyParts3D no
# trae color propio). Convencion confirmada en modelos anatomicos 3D reales:
# lado izquierdo/oxigenado = rojos y rosas, lado derecho/desoxigenado =
# azules y morados, arterias = rojo, venas = azul, valvulas = marfil
# (tejido membranoso), via aerea = amarillo-tostado (cartilago), pulmon =
# rosa-gris (tejido sano). Aproximado, no clinico.
COLORS = {
    "venas_cavas": (120, 156, 190, 255),        # sistemica desoxigenada -> azul claro
    "aorta": (176, 48, 42, 255),                 # arterial, oxigenada -> rojo
    "arterias_pulmonares": (52, 74, 110, 255),   # desoxigenada -> azul oscuro
    "venas_pulmonares": (222, 140, 148, 255),    # oxigenada -> rosa
    "auricula_derecha": (135, 172, 205, 255),    # lado derecho -> azul claro
    "auricula_izquierda": (216, 132, 140, 255),  # lado izquierdo -> rosa
    "ventriculo_derecho": (124, 100, 148, 255),  # lado derecho -> morado
    "ventriculo_izquierdo": (208, 116, 100, 255),# lado izquierdo -> salmon
    "valvula_aortica": (232, 222, 200, 255),     # tejido membranoso -> marfil
    "valvula_pulmonar": (232, 222, 200, 255),
    "valvula_bicuspide": (232, 222, 200, 255),
    "valvula_tricuspide": (232, 222, 200, 255),
    "arterias_coronarias": (176, 64, 56, 255),   # arteria -> rojo
    "venas_coronarias": (72, 92, 122, 255),      # vena -> azul oscuro
    "laringe": (206, 186, 140, 255),             # cartilago -> amarillo-tostado
    "traquea": (208, 182, 120, 255),
    "bronquios": (196, 172, 110, 255),
    "pulmones": (206, 164, 158, 255),            # tejido sano -> rosa-gris
}

# metallicFactor=0 es lo importante: sin esto, un mesh con solo color por
# vertice (sin material PBR explicito) exporta con metallicFactor=1 por
# defecto (el default del spec gltf), que bajo luces simples (sin mapa de
# entorno) se ve casi negro sin importar el color. roughness moderado da
# un aspecto organico, ni espejo ni tiza.
MATERIAL_METALLIC = 0.0
MATERIAL_ROUGHNESS = 0.55

MIN_COMPONENT_FACES = 20  # fragmentos mas chicos que esto son ruido de reconstruccion, no anatomia

# Sombreado por curvatura (AO aproximado) + micro-ruido: sin esto un color
# plano por estructura tapa por completo pliegues, crestas y musculos
# papilares que la malla ya tiene -- esto no inventa geometria, solo la
# revela via COLOR_0 (que gltf multiplica contra baseColorFactor).
AO_STRENGTH = 0.42       # cuanto contraste le da la curvatura (0-1)
AO_FLOOR = 0.55          # que tan oscuro puede llegar a ponerse un pliegue
AO_CEILING = 1.18        # que tan brillante puede llegar a ponerse una cresta
NOISE_AMPLITUDE = 0.05   # micro-variacion aleatoria, rompe el aspecto "plastico"


def compute_shading_colors(mesh, seed):
    laplacian = laplacian_calculation(mesh)
    neighbor_avg = laplacian.dot(mesh.vertices)
    curvature = np.einsum("ij,ij->i", mesh.vertices - neighbor_avg, mesh.vertex_normals)

    lo, hi = np.percentile(curvature, [2, 98])
    span = max(hi - lo, 1e-6)
    normalized = np.clip((curvature - lo) / span * 2 - 1, -1, 1)  # -1..1

    shading = 1.0 + normalized * AO_STRENGTH

    rng = np.random.default_rng(seed)
    noise = 1.0 + (rng.random(len(mesh.vertices)) - 0.5) * 2 * NOISE_AMPLITUDE
    shading = np.clip(shading * noise, AO_FLOOR, AO_CEILING)

    gray = np.clip(shading * 255, 0, 255).astype(np.uint8)
    alpha = np.full_like(gray, 255)
    return np.stack([gray, gray, gray, alpha], axis=1)


def clean_and_smooth(mesh):
    """Descarta fragmentos diminutos (ruido) y suaviza donde es seguro.

    Cada pieza de BodyParts3D es un recorte de un atlas continuo -- queda
    con bordes abiertos donde se separo de la estructura vecina (no es
    watertight). Suavizar (Taubin) un borde abierto lo distorsiona en picos
    largos -- probado empiricamente sobre el arbol bronquial y los grandes
    vasos. Por eso el suavizado geometrico solo se aplica a componentes que
    SI son superficies cerradas; el resto solo recibe normales suaves por
    vertice (no mueve ningun vertice, cero riesgo de deformar la anatomia,
    pero igual resuelve el aspecto "tosco" de las normales planas).
    """
    components = mesh.split(only_watertight=False)
    if len(components) == 0:
        components = [mesh]

    kept = [c for c in components if len(c.faces) >= MIN_COMPONENT_FACES]
    if not kept:
        kept = list(components)

    for part in kept:
        if len(part.vertices) < 4:
            continue
        part.merge_vertices()
        if part.is_watertight:
            trimesh.smoothing.filter_taubin(part, lamb=0.5, nu=0.53, iterations=10)

    merged = trimesh.util.concatenate(kept) if len(kept) > 1 else kept[0]
    merged._cache.delete("vertex_normals")
    merged.vertex_normals  # fuerza el calculo antes de exportar
    return merged


def load_manifest():
    rows = []
    with open(MANIFEST, newline="", encoding="utf-8") as f:
        for r in csv.reader(f):
            if len(r) < 4:
                continue
            rows.append({"fj": r[0], "bp": r[1], "fma": r[2], "name": r[3]})
    return rows


def resolve_groups(rows):
    compiled = {sid: [re.compile(p, re.IGNORECASE) for p in pats] for sid, pats in GROUPS.items()}
    resolved = {}
    for sid, pats in compiled.items():
        matched = [row for row in rows if any(p.search(row["name"]) for p in pats)]
        seen_bp = set()
        deduped = []
        for row in matched:
            if row["bp"] in seen_bp:
                continue
            seen_bp.add(row["bp"])
            deduped.append(row)
        resolved[sid] = deduped
    return resolved


def find_obj_path(fj_id):
    matches = glob.glob(os.path.join(MESHES_DIR, f"{fj_id}_*.obj"))
    return matches[0] if matches else None


def main():
    rows = load_manifest()
    resolved = resolve_groups(rows)

    scene = trimesh.Scene()
    missing = []
    summary = []

    for sid, entries in resolved.items():
        pieces = []
        for row in entries:
            path = find_obj_path(row["fj"])
            if not path or not os.path.exists(path):
                missing.append(f"{sid}: {row['fj']} ({row['name']}) -> archivo no encontrado")
                continue
            if os.path.getsize(path) < 1024:
                # Un .obj real de BodyParts3D pesa varios KB o mas; un archivo
                # de ~130 bytes es casi siempre un puntero de Git LFS sin
                # descargar (falto 'git lfs pull' para este id).
                missing.append(f"{sid}: {row['fj']} ({row['name']}) -> parece un puntero LFS sin descargar")
                continue
            try:
                mesh = trimesh.load(path, force="mesh", process=False)
            except Exception as exc:  # noqa: BLE001
                missing.append(f"{sid}: {row['fj']} ({row['name']}) -> error al cargar: {exc}")
                continue
            if mesh.vertices.shape[0] == 0:
                missing.append(f"{sid}: {row['fj']} ({row['name']}) -> malla vacia tras cargar")
                continue
            pieces.append(mesh)

        if not pieces:
            summary.append(f"{sid}: 0 piezas (SIN MALLA)")
            continue

        merged = trimesh.util.concatenate(pieces) if len(pieces) > 1 else pieces[0]
        merged = clean_and_smooth(merged)

        color = COLORS.get(sid, (200, 200, 200, 255))
        base_material = trimesh.visual.material.PBRMaterial(
            baseColorFactor=[c / 255.0 for c in color],
            metallicFactor=MATERIAL_METALLIC,
            roughnessFactor=MATERIAL_ROUGHNESS,
            doubleSided=True,
        )
        shading_colors = compute_shading_colors(merged, seed=abs(hash(sid)) % (2**32))
        visuals = trimesh.visual.color.ColorVisuals(merged, vertex_colors=shading_colors)
        visuals.material = base_material
        merged.visual = visuals

        scene.add_geometry(merged, node_name=sid, geom_name=sid)
        summary.append(f"{sid}: {len(pieces)} piezas fusionadas, {len(merged.vertices)} vertices")

    if len(scene.geometry) == 0:
        print("No se pudo cargar NINGUNA malla real. Piezas no encontradas:")
        for line in missing:
            print(" ", line)
        print()
        print(
            "Revisa que hayas corrido 'git lfs pull --include=...' con el patron completo "
            "de lfs_include_pattern.txt DENTRO de la carpeta clonada del repositorio, y que "
            "MANIFEST.csv / meshes/ existan en el directorio donde corres este script."
        )
        return

    scene.export(OUTPUT)

    print("=== Resumen ===")
    for line in summary:
        print(" ", line)
    print()
    if missing:
        print("=== Piezas no encontradas (revisa que git lfs pull haya traido todo) ===")
        for line in missing:
            print(" ", line)
        print()
    print(f"Exportado: {OUTPUT}")
    print("Estructuras SIN malla propia (van solo como nodo conceptual):", HUB_ONLY)


if __name__ == "__main__":
    main()
