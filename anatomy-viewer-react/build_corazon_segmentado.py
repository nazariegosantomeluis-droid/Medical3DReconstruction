"""
Arma corazon-segmentado.glb a partir del set BodyParts3D 4.3.

Corre esto DESPUES de:
    git clone https://github.com/olivercase/body_parts_3d_api.git
    cd body_parts_3d_api
    git lfs install
    git lfs pull --include="<pega aqui el contenido de lfs_include_pattern.txt>"
    pip install trimesh numpy
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
# trae color propio). Aproximado, no clinico.
COLORS = {
    "venas_cavas": (90, 110, 190, 255),
    "aorta": (200, 60, 70, 255),
    "arterias_pulmonares": (150, 70, 190, 255),
    "venas_pulmonares": (90, 140, 200, 255),
    "auricula_derecha": (190, 110, 120, 255),
    "auricula_izquierda": (190, 90, 100, 255),
    "ventriculo_derecho": (170, 70, 80, 255),
    "ventriculo_izquierdo": (150, 40, 50, 255),
    "valvula_aortica": (230, 210, 160, 255),
    "valvula_pulmonar": (220, 200, 150, 255),
    "valvula_bicuspide": (225, 205, 155, 255),
    "valvula_tricuspide": (235, 215, 165, 255),
    "arterias_coronarias": (210, 40, 50, 255),
    "venas_coronarias": (60, 90, 180, 255),
    "laringe": (225, 220, 210, 255),
    "traquea": (215, 210, 200, 255),
    "bronquios": (200, 190, 180, 255),
    "pulmones": (225, 190, 195, 255),
}


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

        color = COLORS.get(sid, (200, 200, 200, 255))
        merged.visual = trimesh.visual.ColorVisuals(
            merged, vertex_colors=np.tile(color, (merged.vertices.shape[0], 1))
        )

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
