// El .glb trae dos especímenes reales que no comparten coordenadas: el
// corazón completo (ex-vivo, micro-CT sincrotrón) y las 18 piezas internas
// del atlas BodyParts3D. Cada uno vive bajo su propio nodo-grupo en el
// árbol del glTF (ver anatomy-viewer-react/build_corazon_segmentado.py y
// merge_real_heart.py) para poder mostrar uno a la vez sin que se vean
// superpuestos como si fueran el mismo cuerpo.
export const GROUP_NODE_NAMES = {
  atlas_bodyparts3d: "grupo_atlas_bodyparts3d",
  especimen_real: "grupo_especimen_real",
};

export const DEFAULT_GROUP = "atlas_bodyparts3d";
