"""
Agrega el pulmon reconstruido con el pipeline PROPIO del repo (medical3d:
umbral de Hounsfield + componentes conexas + marching cubes, sobre la TC
real data/volumes/CTChest.nrrd) como un TERCER grupo-especimen dentro de
corazon-segmentado.glb -- junto al atlas BodyParts3D y al corazon real
ex-vivo, pero en su propio nodo (grupo_reconstruccion_propia), porque es
un cuerpo/escaneo real distinto que tampoco comparte coordenadas con los
otros dos.

Corre esto DESPUES de generar la malla con el pipeline principal:
    python3 main.py --input data/volumes/CTChest.nrrd --organ lungs \
        --metrics-json outputs/lungs_metrics.json
desde la raiz del repo, y despues, desde dentro de anatomy-viewer-react/:
    python3 add_pulmon_propio.py
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
LUNGS_OBJ = os.path.join(_REPO_ROOT, "outputs", "lungs.obj")
METRICS_JSON = os.path.join(_REPO_ROOT, "outputs", "lungs_metrics.json")
OUT_PATH = ATLAS_PATH  # overwrite in place

GROUP_PROPIA = "grupo_reconstruccion_propia"
NODE_NAME = "pulmon_reconstruccion_propia"

# Mismo tono que "pulmones" en el atlas BodyParts3D (ver build_corazon_segmentado.py)
# -- es el mismo organo, debe leerse como el mismo organo, solo que esta
# malla la genero el propio pipeline del repo en vez de venir de un atlas externo.
LUNG_COLOR = (206, 164, 158, 255)
MATERIAL_METALLIC = 0.0
MATERIAL_ROUGHNESS = 0.55

# Decimar para la web: 371k triangulos (ya reducidos por el propio pipeline
# desde la malla cruda de marching cubes) siguen siendo demasiado para un
# visor interactivo en un celular que escanea el QR -- las otras piezas de
# esta misma escena son ordenes de magnitud mas livianas. No es un
# resultado cientifico lo que se liviana, es la copia de presentacion web;
# las metricas reales (volumen, area, vertices/triangulos) del pipeline
# siguen siendo las de outputs/lungs_metrics.json, no las de este archivo.
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


def load_lung_mesh():
    mesh = trimesh.load(LUNGS_OBJ, force="mesh", process=False)

    # El volumen viene en convencion ITK/DICOM (X=Izquierda, Y=Posterior,
    # Z=Superior, mano derecha -- ver README). three.js usa Y-arriba, mano
    # derecha. Esta es una rotacion PROPIA (det=+1, (x,y,z)->(x,z,-y)): no
    # espeja nada, asi que el winding/las normales siguen siendo correctas
    # sin tener que re-flipearlas a mano.
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
        baseColorFactor=[c / 255.0 for c in LUNG_COLOR],
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
# El unico nodo que vive en el grupo del especimen real (ver
# merge_real_heart.py) -- todo lo demas que no sea la pieza nueva es del
# atlas BodyParts3D. Hardcodeado a proposito en vez de recorrer el grafo
# de trimesh: es mas simple y no depende de la API interna del grafo, que
# ya cambio una vez entre versiones de trimesh en este mismo proyecto.
REAL_SPECIMEN_NODES = {"corazon"}


def main():
    scene = trimesh.load(ATLAS_PATH, process=False)
    # Idempotencia: si este script ya corrio antes sobre este archivo, el
    # nodo ya esta ahi -- sin este filtro, correrlo de nuevo duplicaria la
    # malla.
    existing_geometry = {name: geom for name, geom in scene.geometry.items() if name != NODE_NAME}
    print("Piezas existentes conservadas:", len(existing_geometry))

    lung_mesh = load_lung_mesh()
    print(f"Pulmon propio: {len(lung_mesh.vertices)} vertices, {len(lung_mesh.faces)} triangulos (decimado para web)")

    combined = trimesh.Scene()
    combined.graph.update(frame_to=GROUP_ATLAS, frame_from=combined.graph.base_frame, matrix=np.eye(4))
    combined.graph.update(frame_to=GROUP_REAL, frame_from=combined.graph.base_frame, matrix=np.eye(4))
    combined.graph.update(frame_to=GROUP_PROPIA, frame_from=combined.graph.base_frame, matrix=np.eye(4))

    for name, geom in existing_geometry.items():
        group = GROUP_REAL if name in REAL_SPECIMEN_NODES else GROUP_ATLAS
        combined.add_geometry(geom, node_name=name, geom_name=name, parent_node_name=group)

    combined.add_geometry(lung_mesh, node_name=NODE_NAME, geom_name=NODE_NAME, parent_node_name=GROUP_PROPIA)

    combined.export(OUT_PATH)
    print(f"\nExportado: {OUT_PATH}")
    print(f"Grupos: {GROUP_ATLAS} ({len(existing_geometry) - len(REAL_SPECIMEN_NODES)} piezas) + "
          f"{GROUP_REAL} ({len(REAL_SPECIMEN_NODES)} pieza) + {GROUP_PROPIA} (1 pieza)")

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
