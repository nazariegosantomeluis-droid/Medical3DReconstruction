// Empareja el nombre de una malla del modelo 3D (tal como Three.js lo lee
// del .glb) con una entrada de estructuras.json, sin exigir que coincidan
// carácter por carácter — normaliza acentos, mayúsculas y separadores antes
// de comparar, porque el nombre real de la malla depende de cómo se haya
// exportado el modelo desde Blender.

function normalize(value) {
  return value
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");
}

export function findStructureByMeshName(meshName, structures) {
  if (!meshName) return null;
  const target = normalize(meshName);
  if (!target) return null;

  const exact = structures.find(
    (structure) =>
      normalize(structure.id) === target ||
      structure.meshNames?.some((alias) => normalize(alias) === target)
  );
  if (exact) return exact;

  // Coincidencia parcial como último recurso: útil cuando Blender agrega
  // sufijos numéricos (p. ej. "Corazon.002") o prefijos de la jerarquía.
  return (
    structures.find((structure) => {
      const id = normalize(structure.id);
      return target.includes(id) || id.includes(target);
    }) || null
  );
}
