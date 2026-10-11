"""
Agrega el corazon reconstruido con el pipeline PROPIO del repo (medical3d:
level set geodesico sensible a bordes, sobre la TC real
data/volumes/CTChest.nrrd) como SEGUNDO nodo dentro de
grupo_reconstruccion_propia -- junto al pulmon propio ya agregado por
add_pulmon_propio.py. Viene de la MISMA tomografia y la MISMA convencion
de ejes, asi que comparte el mismo sistema de coordenadas que el pulmon:
al verlos juntos en el visor, corazon y pulmones quedan en su posicion
anatomica relativa real, no superpuestos por coincidencia.

Corre esto DESPUES de generar la malla con el pipeline principal:
    python3 main.py --input data/volumes/CTChest.nrrd --organ heart \
        --metrics-json outputs/heart_metrics.json
desde la raiz del repo, y despues, desde dentro de anatomy-viewer-react/:
    python3 add_corazon_propio.py
Modifica public/models/corazon-segmentado.glb en el lugar.
"""

import json
import os

import numpy as np
import trimesh
from trimesh.smoothing import laplacian_calculation

_HERE = os.path.dirname(__file__)
_REPO_ROOT = os.path.dirname(_HERE)
ATLAS_PATH = os.path.join(_HERE, "public", "models", "corazon-segmentado.glb")
HEART_OBJ = os.path.join(_REPO_ROOT, "outputs", "heart.obj")
METRICS_JSON = os.path.join(_REPO_ROOT, "outputs", "heart_metrics.json")
OUT_PATH = ATLAS_PATH  # overwrite in place

GROUP_PROPIA = "grupo_reconstruccion_propia"
NODE_NAME = "corazon_reconstruccion_propia"

# Mismo rojo de musculo cardiaco real que usa el corazon ex-vivo
# (merge_real_heart.py) -- es el mismo organo, debe leerse como el mismo
# organo, solo que esta malla la genero el propio pipeline del repo sobre
# una TC in-vivo en vez de venir de un especimen ex-vivo escaneado por
# micro-CT.
HEART_COLOR = (168, 66, 58, 255)
MATERIAL_METALLIC = 0.0
MATERIAL_ROUGHNESS = 0.55

# El pipeline ya entrega una malla liviana para este organo (ver metricas
# en outputs/heart_metrics.json), pero se decima igual por consistencia
# con el resto de piezas de esta escena web.
TARGET_FACE_COUNT = 45000

AO_STRENGTH = 0.42
AO_FLOOR = 0.55
AO_CEILING = 1.18
NOISE_AMPLITUDE = 0.05


def compute_shading_colors(mesh, seed):
    laplacian = laplacian_calculation(mesh)
    neighbor_avg = laplacian.dot(mesh.vertices)
    curvature = np.einsum("ij,ij->i", mesh.vertices - neighbor_avg, mesh.vertex_normals)

    lo, hi = np.percentile(curvature, [2, 98])
    span = max(hi - lo, 1e-6)
    normalized = np.clip((curvature - lo) / span * 2 - 1, -1, 1)

    shading = 1.0 + normalized * AO_STRENGTH
    rng = np.random.default_rng(seed)
    noise = 1.0 + (rng.random(len(mesh.vertices)) - 0.5) * 2 * NOISE_AMPLITUDE
    shading = np.clip(shading * noise, AO_FLOOR, AO_CEILING)

    gray = np.clip(shading * 255, 0, 255).astype(np.uint8)
    alpha = np.full_like(gray, 255)
    return np.stack([gray, gray, gray, alpha], axis=1)


def load_heart_mesh():
    mesh = trimesh.load(HEART_OBJ, force="mesh", process=False)

    # Misma rotacion propia (det=+1) que usa add_pulmon_propio.py para la
    # MISMA tomografia: ITK/DICOM (X=Izquierda, Y=Posterior, Z=Superior,
    # mano derecha) -> three.js (Y-arriba, mano derecha), (x,y,z)->(x,z,-y).
    R = np.array(
        [
            [1, 0, 0],
            [0, 0, 1],
            [0, -1, 0],
        ],
        dtype=float,
    )
    transform = np.eye(4)
    transform[:3, :3] = R
    mesh.apply_transform(transform)

    if len(mesh.faces) > TARGET_FACE_COUNT:
        mesh = mesh.simplify_quadric_decimation(face_count=TARGET_FACE_COUNT)

    mesh.merge_vertices()
    mesh._cache.delete("vertex_normals")
    mesh.vertex_normals  # fuerza el calculo antes de exportar

    base_material = trimesh.visual.material.PBRMaterial(
        baseColorFactor=[c / 255.0 for c in HEART_COLOR],
        metallicFactor=MATERIAL_METALLIC,
        roughnessFactor=MATERIAL_ROUGHNESS,
        doubleSided=True,
    )
    shading_colors = compute_shading_colors(mesh, seed=abs(hash(NODE_NAME)) % (2**32))
    visuals = trimesh.visual.color.ColorVisuals(mesh, vertex_colors=shading_colors)
    visuals.material = base_material
    mesh.visual = visuals

    return mesh


GROUP_ATLAS = "grupo_atlas_bodyparts3d"
GROUP_REAL = "grupo_especimen_real"
# Membresia de grupo hardcodeada a proposito (no se recorre el grafo de
# trimesh para inferirla): la API interna del grafo ya cambio una vez
# entre versiones de trimesh en este mismo proyecto (ver
# add_pulmon_propio.py), asi que es mas simple y mas robusto nombrar los
# nodos que no son del atlas explicitamente.
REAL_SPECIMEN_NODES = {"corazon"}
PROPIA_NODES = {"pulmon_reconstruccion_propia"}


def main():
    scene = trimesh.load(ATLAS_PATH, process=False)
    # Idempotencia: si este script ya corrio antes, el nodo ya esta ahi --
    # sin este filtro, correrlo de nuevo duplicaria la malla.
    existing_geometry = {name: geom for name, geom in scene.geometry.items() if name != NODE_NAME}
    print("Piezas existentes conservadas:", len(existing_geometry))

    heart_mesh = load_heart_mesh()
    print(f"Corazon propio: {len(heart_mesh.vertices)} vertices, {len(heart_mesh.faces)} triangulos (decimado para web)")

    combined = trimesh.Scene()
    combined.graph.update(frame_to=GROUP_ATLAS, frame_from=combined.graph.base_frame, matrix=np.eye(4))
    combined.graph.update(frame_to=GROUP_REAL, frame_from=combined.graph.base_frame, matrix=np.eye(4))
    combined.graph.update(frame_to=GROUP_PROPIA, frame_from=combined.graph.base_frame, matrix=np.eye(4))

    for name, geom in existing_geometry.items():
        if name in REAL_SPECIMEN_NODES:
            group = GROUP_REAL
        elif name in PROPIA_NODES:
            group = GROUP_PROPIA
        else:
            group = GROUP_ATLAS
        combined.add_geometry(geom, node_name=name, geom_name=name, parent_node_name=group)

    combined.add_geometry(heart_mesh, node_name=NODE_NAME, geom_name=NODE_NAME, parent_node_name=GROUP_PROPIA)

    combined.export(OUT_PATH)
    print(f"\nExportado: {OUT_PATH}")

    if os.path.exists(METRICS_JSON):
        with open(METRICS_JSON) as f:
            metrics = json.load(f)
        print("\nMetricas reales del pipeline (no de esta copia web decimada):")
        print(" volumen_ml:", round(metrics["metrics"]["volume_ml"], 1))
        print(" area_mm2:", round(metrics["metrics"]["surface_area_mm2"], 1))
        print(" vertices/triangulos (pipeline):", metrics["metrics"]["num_vertices"], "/", metrics["metrics"]["num_triangles"])
        print(" watertight:", metrics["validation"]["mesh_quality"]["is_watertight"])


if __name__ == "__main__":
    main()
