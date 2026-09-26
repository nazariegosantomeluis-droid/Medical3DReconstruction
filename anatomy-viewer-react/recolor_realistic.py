"""
Utilidad de ajuste rapido: re-aplica esta paleta y este material sobre un
corazon-segmentado.glb YA armado, sin re-descargar nada de BodyParts3D ni
volver a correr build_corazon_segmentado.py / merge_real_heart.py. Util si
solo quieres retocar un color. Corre desde dentro de anatomy-viewer-react/:
    python3 recolor_realistic.py

El material importa mas que el color: las mallas tenian ColorVisuals
(color por vertice) sin material PBR explicito, asi que el exportador de
trimesh les puso metallicFactor=1/roughnessFactor=1 por defecto (los
valores por defecto del spec gltf) -- eso hace que CUALQUIER superficie se
vea casi negra bajo luces direccionales simples, sin mapa de entorno. La
causa de "todo se ve opaco/negro" no era el color, era el material.

Convencion de color (confirmada por busqueda: modelos medicos 3D reales
codifican por oxigenacion -- lado izquierdo = rojo/rosado, lado derecho =
azul/morado -- arterias = rojo, venas = azul, valvulas = marfil palido,
via aerea = amarillo/tostado, pulmon = rosa-gris).
"""

import os

import trimesh

_HERE = os.path.dirname(__file__)
PATHS = [os.path.join(_HERE, "public", "models", "corazon-segmentado.glb")]

# RGBA 0-255. Lado izquierdo/oxigenado = rojos y rosas. Lado derecho/
# desoxigenado = azules y morados. Valvulas = marfil (tejido membranoso).
# Via aerea = amarillo-tostado (cartilago). Pulmon = rosa-gris.
COLORS = {
    "corazon": (168, 66, 58, 255),            # musculo cardiaco real
    "aorta": (176, 48, 42, 255),               # arterial, oxigenada
    "arterias_pulmonares": (52, 74, 110, 255), # desoxigenada -> azul oscuro
    "venas_pulmonares": (222, 140, 148, 255),  # oxigenada -> rosa
    "venas_cavas": (120, 156, 190, 255),       # sistemica desoxigenada -> azul claro
    "auricula_derecha": (135, 172, 205, 255),  # lado derecho -> azul claro
    "auricula_izquierda": (216, 132, 140, 255),# lado izquierdo -> rosa
    "ventriculo_derecho": (124, 100, 148, 255),# lado derecho -> morado
    "ventriculo_izquierdo": (208, 116, 100, 255), # lado izquierdo -> salmon
    "valvula_aortica": (232, 222, 200, 255),   # tejido membranoso -> marfil
    "valvula_pulmonar": (232, 222, 200, 255),
    "valvula_bicuspide": (232, 222, 200, 255),
    "valvula_tricuspide": (232, 222, 200, 255),
    "arterias_coronarias": (176, 64, 56, 255), # arteria -> rojo
    "venas_coronarias": (72, 92, 122, 255),    # vena -> azul oscuro
    "laringe": (206, 186, 140, 255),           # cartilago -> amarillo-tostado
    "traquea": (208, 182, 120, 255),
    "bronquios": (196, 172, 110, 255),
    "pulmones": (206, 164, 158, 255),          # tejido pulmonar sano -> rosa-gris
}

METALLIC = 0.0
ROUGHNESS = 0.55


def to_float(rgba255):
    return [c / 255.0 for c in rgba255]


def main():
    for path in PATHS:
        scene = trimesh.load(path, process=False)
        for name, mesh in scene.geometry.items():
            color = COLORS.get(name)
            if color is None:
                print(f"AVISO: sin color definido para '{name}', se deja como esta")
                continue
            mesh.visual = trimesh.visual.TextureVisuals(
                material=trimesh.visual.material.PBRMaterial(
                    baseColorFactor=to_float(color),
                    metallicFactor=METALLIC,
                    roughnessFactor=ROUGHNESS,
                    doubleSided=True,
                )
            )
        scene.export(path)
        print(f"Recoloreado: {path} ({len(scene.geometry)} piezas)")


if __name__ == "__main__":
    main()
