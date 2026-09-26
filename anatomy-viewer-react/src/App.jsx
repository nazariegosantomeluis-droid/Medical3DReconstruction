import { useCallback, useMemo, useState } from "react";
import { Loader } from "@react-three/drei";
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
  // dejar visible y ocultar las demás del grupo activo.
  const selectedMeshName = selectedId ? structureIdToMeshName[selectedId] ?? null : unmatchedMesh;
  // Mallas de las estructuras "relacionadas" (mismo mapa de conexiones
  // clínicas del panel) — Model.jsx las deja muy tenues en vez de ocultarlas,
  // como contexto anatómico alrededor de la seleccionada.
  const relatedMeshNames = useMemo(() => {
    if (!selectedStructure?.relacionadas) return [];
    return selectedStructure.relacionadas
      .map((id) => structureIdToMeshName[id])
      .filter(Boolean);
  }, [selectedStructure, structureIdToMeshName]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg font-sans text-ink">
      <Sidebar
        debugMode={debugMode}
        onToggleDebug={() => setDebugMode((prev) => !prev)}
        activeGroup={activeGroup}
        selectedId={selectedId}
        onSelect={handleSelectRelated}
      />

      <main className="relative flex-1 overflow-hidden">
        <div className="pointer-events-none absolute left-5 top-5 z-10 max-w-sm">
          <p className="text-xs text-ink-dim">
            {hoveredMesh
              ? `Estructura bajo el cursor: ${hoveredMesh}`
              : "Arrastra para rotar · rueda para hacer zoom · clic para más información"}
          </p>
        </div>

        <ModelErrorBoundary fallback={<NoModelFallback />}>
          <Scene
            modelUrl={MODEL_URL}
            onSelect={handleSelect}
            onHoverChange={handleHoverChange}
            onMeshNames={handleMeshNames}
            selectedMeshName={selectedMeshName}
            relatedMeshNames={relatedMeshNames}
            activeGroupNodeName={GROUP_NODE_NAMES[activeGroup]}
          />
        </ModelErrorBoundary>
        <Loader
          containerStyles={{ background: "#17181a" }}
          innerStyles={{ width: "12rem" }}
          barStyles={{ background: "#c0525b" }}
          dataStyles={{ color: "#9a9da2", fontFamily: "Inter, sans-serif", fontSize: "0.75rem" }}
          dataInterpolation={(p) => `Cargando modelo… ${p.toFixed(0)}%`}
        />

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
          <footer className="pointer-events-none absolute bottom-3 right-4 z-10 max-w-xs text-right text-[0.62rem] leading-snug text-ink-faint">
            Piezas internas: BodyParts3D/Anatomography, © Database Center for Life Science (DBCLS) —
            CC BY-SA 2.1 Japan. Corazón completo: espécimen ex-vivo real (LADAF-2021-17, micro-CT
            sincrotrón).
          </footer>
        ) : null}
      </main>
    </div>
  );
}

function Sidebar({ debugMode, onToggleDebug, activeGroup, selectedId, onSelect }) {
  return (
    <aside className="flex w-80 shrink-0 flex-col border-r border-border bg-surface">
      <div className="flex items-center gap-2.5 border-b border-border px-4 py-4">
        <svg
          className="h-5 w-5 shrink-0 text-accent"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <circle cx="12" cy="13" r="8.4" stroke="currentColor" strokeWidth="1.3" />
          <circle cx="12" cy="13" r="5" stroke="currentColor" strokeWidth="1.3" opacity="0.6" />
          <circle cx="12" cy="13" r="1.6" fill="currentColor" />
          <path d="M4.2 6 L19.8 6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
        </svg>
        <div className="min-w-0">
          <h1 className="truncate text-sm font-semibold text-ink">Visor cardiorrespiratorio</h1>
          <p className="truncate text-[0.68rem] text-ink-faint">Mapa de conexiones clínicas</p>
        </div>
      </div>

      <div className="border-b border-border px-4 py-3">
        <p className="text-[0.68rem] font-semibold uppercase tracking-wider text-ink-faint">
          Viendo ahora
        </p>
        <p className="mt-1 text-sm text-ink">{GROUP_LABELS[activeGroup]}</p>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4" aria-label="Índice de estructuras">
        <StructureIndex structures={estructuras} selectedId={selectedId} onSelect={onSelect} />
      </nav>

      <div className="border-t border-border px-4 py-3">
        <button
          type="button"
          onClick={onToggleDebug}
          className={`w-full rounded-md border px-3 py-1.5 text-xs font-semibold transition ${
            debugMode
              ? "border-warn bg-warn/20 text-warn"
              : "border-border bg-surface-raised text-ink-dim hover:text-ink"
          }`}
        >
          {debugMode ? "Modo Debug: ACTIVO" : "Modo Debug"}
        </button>
      </div>
    </aside>
  );
}

function NoModelFallback() {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-bg p-6">
      <div className="max-w-sm rounded-lg border border-border bg-surface p-5 text-center">
        <p className="text-sm font-semibold text-ink">Todavía no hay un modelo 3D cargado</p>
        <p className="mt-2 text-xs leading-relaxed text-ink-dim">
          Coloca tu archivo <code className="rounded bg-surface-raised px-1 py-0.5">.glb</code> en{" "}
          <code className="rounded bg-surface-raised px-1 py-0.5">public/models/</code> y actualiza
          la constante <code className="rounded bg-surface-raised px-1 py-0.5">MODEL_URL</code> en{" "}
          <code className="rounded bg-surface-raised px-1 py-0.5">App.jsx</code> con su nombre real.
        </p>
      </div>
    </div>
  );
}
