// El .glb trae TRES especímenes reales que no comparten coordenadas: el
// corazón completo (ex-vivo, micro-CT sincrotrón), las 18 piezas internas
// del atlas BodyParts3D, y el pulmón reconstruido con el pipeline PROPIO
// del repo (umbral de Hounsfield + marching cubes sobre una TC de tórax
// real, ver ../add_pulmon_propio.py). Cada uno vive bajo su propio
// nodo-grupo en el árbol del glTF (ver anatomy-viewer-react/
// build_corazon_segmentado.py, merge_real_heart.py y add_pulmon_propio.py)
// para poder mostrar uno a la vez sin que se vean superpuestos como si
// fueran el mismo cuerpo.
export const GROUP_NODE_NAMES = {
  atlas_bodyparts3d: "grupo_atlas_bodyparts3d",
  especimen_real: "grupo_especimen_real",
  reconstruccion_propia: "grupo_reconstruccion_propia",
};

export const DEFAULT_GROUP = "atlas_bodyparts3d";
