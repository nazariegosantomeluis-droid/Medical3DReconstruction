"""
Agrega el corazon real ex-vivo (extraido con extract_heart_mesh.py) como
una 19a pieza dentro de corazon-segmentado.glb -- en su propio nodo-grupo,
separado de las 18 piezas del atlas BodyParts3D, porque son dos cuerpos
reales distintos que no comparten coordenadas (ver notaEspecimen en
estructuras.json). Corre esto DESPUES de extract_heart_mesh.py, desde
dentro de anatomy-viewer-react/:
    python3 merge_real_heart.py
Modifica public/models/corazon-segmentado.glb en el lugar.
"""

import base64
import json
import os

import numpy as np
import trimesh
from trimesh.smoothing import laplacian_calculation

_HERE = os.path.dirname(__file__)
ATLAS_PATH = os.path.join(_HERE, "public", "models", "corazon-segmentado.glb")
HEART_MESH_JSON = os.path.join(_HERE, "heart_mesh.json")
OUT_PATH = ATLAS_PATH  # overwrite in place

GROUP_ATLAS = "grupo_atlas_bodyparts3d"
GROUP_REAL = "grupo_especimen_real"

HEART_COLOR = (168, 66, 58, 255)  # musculo cardiaco real, no el rojo de acento de la UI
MATERIAL_METALLIC = 0.0
MATERIAL_ROUGHNESS = 0.55

# Mismo sombreado por curvatura + micro-ruido que build_corazon_segmentado.py
# (ver ese archivo para la explicacion completa) -- revela crestas y surcos
# reales del especimen ex-vivo que un color plano tapaba por completo.
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


def decode_heart_mesh():
    with open(HEART_MESH_JSON) as f:
        mesh_data = json.load(f)

    positions = np.frombuffer(base64.b64decode(mesh_data["positions_b64"]), dtype=np.float32).reshape(-1, 3)
    indices = np.frombuffer(base64.b64decode(mesh_data["indices_b64"]), dtype=np.uint32).reshape(-1, 3)

    mesh = trimesh.Trimesh(vertices=positions, faces=indices, process=False)
    # Esta malla SI es una superficie cerrada real (marching cubes sobre un
    # volumen CT completo), asi que a diferencia de las piezas recortadas de
    # BodyParts3D, aqui el suavizado geometrico es seguro.
    mesh.merge_vertices()
    if mesh.is_watertight:
        trimesh.smoothing.filter_taubin(mesh, lamb=0.5, nu=0.53, iterations=10)
    mesh._cache.delete("vertex_normals")
    mesh.vertex_normals
    # material PBR explicito, no color por vertice puro: sin esto el gltf
    # exporta con metallicFactor=1 por defecto, que se ve casi negro sin mapa
    # de entorno (ver build_corazon_segmentado.py para la explicacion
    # completa). El sombreado por curvatura se agrega ADEMAS, como COLOR_0,
    # que gltf multiplica contra baseColorFactor -- revela pliegues y
    # musculos papilares reales sin tocar el color anatomico base.
    base_material = trimesh.visual.material.PBRMaterial(
        baseColorFactor=[c / 255.0 for c in HEART_COLOR],
        metallicFactor=MATERIAL_METALLIC,
        roughnessFactor=MATERIAL_ROUGHNESS,
        doubleSided=True,
    )
    shading_colors = compute_shading_colors(mesh, seed=abs(hash("corazon")) % (2**32))
    visuals = trimesh.visual.color.ColorVisuals(mesh, vertex_colors=shading_colors)
    visuals.material = base_material
    mesh.visual = visuals
    return mesh


def main():
    atlas_scene = trimesh.load(ATLAS_PATH, process=False)
    # Si este script ya corrió antes sobre este mismo archivo, "corazon" ya
    # está adentro (bajo GROUP_REAL) -- sin este filtro, volver a correrlo
    # lo metería también en GROUP_ATLAS y crearía un "corazon_1" duplicado.
    atlas_geometry = {name: geom for name, geom in atlas_scene.geometry.items() if name != "corazon"}
    print("Piezas del atlas cargadas:", list(atlas_geometry.keys()))

    heart_mesh = decode_heart_mesh()
    print(f"Corazón real: {len(heart_mesh.vertices)} vértices, {len(heart_mesh.faces)} triángulos")

    combined = trimesh.Scene()
    # Los nodos-grupo tienen que existir en el grafo ANTES de que algo los
    # use como parent_node_name, si no trimesh no sabe a qué transform
    # engancharlos al exportar.
    combined.graph.update(frame_to=GROUP_ATLAS, frame_from=combined.graph.base_frame, matrix=np.eye(4))
    combined.graph.update(frame_to=GROUP_REAL, frame_from=combined.graph.base_frame, matrix=np.eye(4))

    for name, geom in atlas_geometry.items():
        combined.add_geometry(geom, node_name=name, geom_name=name, parent_node_name=GROUP_ATLAS)

    combined.add_geometry(heart_mesh, node_name="corazon", geom_name="corazon", parent_node_name=GROUP_REAL)

    combined.export(OUT_PATH)
    print(f"\nExportado: {OUT_PATH}")
    print("Grupos:", GROUP_ATLAS, "(18 piezas) +", GROUP_REAL, "(corazon real ex-vivo)")


if __name__ == "__main__":
    main()
