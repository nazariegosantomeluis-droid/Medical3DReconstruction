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

_HERE = os.path.dirname(__file__)
ATLAS_PATH = os.path.join(_HERE, "public", "models", "corazon-segmentado.glb")
HEART_MESH_JSON = os.path.join(_HERE, "heart_mesh.json")
OUT_PATH = ATLAS_PATH  # overwrite in place

GROUP_ATLAS = "grupo_atlas_bodyparts3d"
GROUP_REAL = "grupo_especimen_real"

HEART_COLOR = (168, 66, 58, 255)  # musculo cardiaco real, no el rojo de acento de la UI
MATERIAL_METALLIC = 0.0
MATERIAL_ROUGHNESS = 0.55


def decode_heart_mesh():
    with open(HEART_MESH_JSON) as f:
        mesh_data = json.load(f)

    positions = np.frombuffer(base64.b64decode(mesh_data["positions_b64"]), dtype=np.float32).reshape(-1, 3)
    indices = np.frombuffer(base64.b64decode(mesh_data["indices_b64"]), dtype=np.uint32).reshape(-1, 3)

    mesh = trimesh.Trimesh(vertices=positions, faces=indices, process=False)
    # material PBR explicito, no color por vertice: sin esto el gltf exporta
    # con metallicFactor=1 por defecto, que se ve casi negro sin mapa de
    # entorno (ver build_corazon_segmentado.py para la explicacion completa).
    mesh.visual = trimesh.visual.TextureVisuals(
        material=trimesh.visual.material.PBRMaterial(
            baseColorFactor=[c / 255.0 for c in HEART_COLOR],
            metallicFactor=MATERIAL_METALLIC,
            roughnessFactor=MATERIAL_ROUGHNESS,
            doubleSided=True,
        )
    )
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
