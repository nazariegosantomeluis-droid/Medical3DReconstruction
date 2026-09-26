import { useCallback, useMemo, useState } from "react";
import Scene from "./components/Scene";
import InfoPanel from "./components/InfoPanel";
import DebugPanel from "./components/DebugPanel";
import StructureIndex from "./components/StructureIndex";
import ModelErrorBoundary from "./components/ModelErrorBoundary";
import estructuras from "./data/estructuras.json";
import { findStructureByMeshName } from "./utils/matchStructure";
import { GROUP_NODE_NAMES, DEFAULT_GROUP } from "./constants/modelGroups";

const GROUP_LABELS = {
  atlas_bodyparts3d: "Piezas internas (atlas BodyParts3D)",
  especimen_real: "Corazón completo (espécimen real)",
};

// Cambia esto por el nombre real de tu archivo dentro de public/models/.
// Se arma sobre BASE_URL (en vez de un "/models/..." fijo) para que el
// modelo se siga encontrando cuando el sitio se publique bajo una subruta,
// como /anatomy-viewer/, y no solo en la raíz del dominio.
const MODEL_URL = `${import.meta.env.BASE_URL}models/corazon-segmentado.glb`;

export default function App() {
  const [hoveredMesh, setHoveredMesh] = useState(null);
  const [meshInventory, setMeshInventory] = useState([]);

  // Modo Debug: reporta el nombre crudo de cualquier malla bajo el cursor o
  // clickeada, sin abrir el Cuadro de Conocimiento — solo para diagnosticar
  // un .glb nuevo. Apagado por defecto: la experiencia normal es el mapa de
  // conexiones de abajo.
  const [debugMode, setDebugMode] = useState(false);
  const [debugSelectedMesh, setDebugSelectedMesh] = useState(null);

  // Selección real (no-debug): o una estructura conocida (selectedId), o una
  // malla cruda que no matcheó ninguna estructura (unmatchedMesh) — nunca
  // las dos a la vez.
  const [selectedId, setSelectedId] = useState(null);
  const [unmatchedMesh, setUnmatchedMesh] = useState(null);

  // El .glb trae dos especímenes reales que no comparten coordenadas: el
  // corazón completo (ex-vivo) y las piezas internas del atlas BodyParts3D.
  // Solo uno está visible a la vez; seleccionar una estructura del otro
  // grupo cambia esto y hace que la cámara se reencuadre a él (ver Model.jsx).
  const [activeGroup, setActiveGroup] = useState(DEFAULT_GROUP);

  const handleHoverChange = useCallback((meshName) => {
    setHoveredMesh(meshName);
  }, []);

  const handleMeshNames = useCallback((inventory) => {
    setMeshInventory(inventory);
  }, []);

  // De cada malla real del modelo cargado, a qué id de estructura
  // corresponde — resuelto una sola vez por inventario para no tener que
  // re-adivinar en cada clic de chip. Es lo que permite que saltar a una
  // estructura relacionada también la resalte en el visor 3D.
  const structureIdToMeshName = useMemo(() => {
    const map = {};
    for (const { name } of meshInventory) {
      const structure = findStructureByMeshName(name, estructuras);
      if (structure && !(structure.id in map)) {
        map[structure.id] = name;
      }
    }
    return map;
  }, [meshInventory]);

  const handleSelect = useCallback(
    (meshName) => {
      if (debugMode) {
        // eslint-disable-next-line no-console
        console.log("[Modo Debug] malla seleccionada:", meshName);
        setDebugSelectedMesh(meshName);
        return;
      }
      const structure = findStructureByMeshName(meshName, estructuras);
      if (structure) {
        setSelectedId(structure.id);
        setUnmatchedMesh(null);
        // Un clic directo en 3D solo puede pasar sobre el grupo que ya está
        // visible, así que el grupo activo no cambia aquí — sí puede
        // cambiar al saltar por un chip (ver handleSelectRelated).
      } else {
        setSelectedId(null);
        setUnmatchedMesh(meshName);
      }
    },
    [debugMode]
  );

  const handleSelectRelated = useCallback((id) => {
    setSelectedId(id);
    setUnmatchedMesh(null);

    const structure = estructuras.find((s) => s.id === id);
    if (structure?.grupo) {
      setActiveGroup(structure.grupo);
    }
  }, []);

  const handleClose = useCallback(() => {
    setSelectedId(null);
    setUnmatchedMesh(null);
  }, []);

  const selectedStructure = selectedId ? estructuras.find((s) => s.id === selectedId) ?? null : null;
  const panelOpen = !debugMode && Boolean(selectedStructure || unmatchedMesh);
  // Nombre de malla real de lo seleccionado, para que Model.jsx sepa cuál
  // dejar opaca y volver transparentes las demás del grupo activo.
  const selectedMeshName = selectedId ? structureIdToMeshName[selectedId] ?? null : unmatchedMesh;

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-slate-900">
      <header className="absolute top-0 left-0 z-10 flex w-full items-start justify-between p-4">
        <div className="pointer-events-none">
          <h1 className="text-lg font-semibold text-white drop-shadow">
            Visor anatómico cardiorrespiratorio
          </h1>
          <p className="mt-1 text-xs text-slate-300">
            {hoveredMesh
              ? `Estructura bajo el cursor: ${hoveredMesh}`
              : "Arrastra para rotar · rueda para hacer zoom · clic para más información"}
          </p>
        </div>

        <div className="pointer-events-auto flex items-center gap-2">
          {!debugMode ? (
            <span className="rounded-md border border-slate-700 bg-slate-800/90 px-3 py-1.5 text-xs text-slate-300">
              Viendo: {GROUP_LABELS[activeGroup]}
            </span>
          ) : null}
          <button
            type="button"
            onClick={() => setDebugMode((prev) => !prev)}
            className={`rounded-md border px-3 py-1.5 text-xs font-semibold transition ${
              debugMode
                ? "border-amber-400 bg-amber-500 text-slate-900 hover:bg-amber-400"
                : "border-slate-600 bg-slate-800 text-slate-200 hover:bg-slate-700"
            }`}
          >
            {debugMode ? "Modo Debug: ACTIVO" : "Modo Debug: inactivo"}
          </button>
        </div>
      </header>

      {!debugMode ? <StructureIndex structures={estructuras} onSelect={handleSelectRelated} /> : null}

      <ModelErrorBoundary fallback={<NoModelFallback />}>
        <Scene
          modelUrl={MODEL_URL}
          onSelect={handleSelect}
          onHoverChange={handleHoverChange}
          onMeshNames={handleMeshNames}
          selectedMeshName={selectedMeshName}
          activeGroupNodeName={GROUP_NODE_NAMES[activeGroup]}
        />
      </ModelErrorBoundary>

      {debugMode ? (
        <DebugPanel
          hoveredMesh={hoveredMesh}
          selectedMesh={debugSelectedMesh}
          meshInventory={meshInventory}
        />
      ) : null}

      {panelOpen ? (
        <InfoPanel
          structure={selectedStructure}
          meshName={unmatchedMesh}
          allStructures={estructuras}
          onClose={handleClose}
          onSelectRelated={handleSelectRelated}
        />
      ) : null}

      {meshInventory.length > 0 ? (
        <footer className="pointer-events-none absolute bottom-2 right-3 z-10 max-w-xs text-right text-[0.62rem] leading-snug text-slate-500">
          Piezas internas: BodyParts3D/Anatomography, © Database Center for Life Science (DBCLS) —
          CC BY-SA 2.1 Japan. Corazón completo: espécimen ex-vivo real (LADAF-2021-17, micro-CT
          sincrotrón).
        </footer>
      ) : null}
    </div>
  );
}

function NoModelFallback() {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-slate-900 p-6">
      <div className="max-w-sm rounded-lg border border-slate-700 bg-slate-800/80 p-5 text-center">
        <p className="text-sm font-semibold text-slate-100">Todavía no hay un modelo 3D cargado</p>
        <p className="mt-2 text-xs leading-relaxed text-slate-400">
          Coloca tu archivo <code className="rounded bg-slate-900 px-1 py-0.5">.glb</code> en{" "}
          <code className="rounded bg-slate-900 px-1 py-0.5">public/models/</code> y actualiza la
          constante <code className="rounded bg-slate-900 px-1 py-0.5">MODEL_URL</code> en{" "}
          <code className="rounded bg-slate-900 px-1 py-0.5">App.jsx</code> con su nombre real.
        </p>
      </div>
    </div>
  );
}
