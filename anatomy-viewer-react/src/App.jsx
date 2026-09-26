import { useCallback, useState } from "react";
import Scene from "./components/Scene";
import InfoPanel from "./components/InfoPanel";
import DebugPanel from "./components/DebugPanel";
import ModelErrorBoundary from "./components/ModelErrorBoundary";
import estructuras from "./data/estructuras.json";
import { findStructureByMeshName } from "./utils/matchStructure";

// Cambia esto por el nombre real de tu archivo dentro de public/models/.
// Se arma sobre BASE_URL (en vez de un "/models/..." fijo) para que el
// modelo se siga encontrando cuando el sitio se publique bajo una subruta,
// como /anatomy-viewer/, y no solo en la raíz del dominio.
const MODEL_URL = `${import.meta.env.BASE_URL}models/corazon-segmentado.glb`;

export default function App() {
  const [selectedMesh, setSelectedMesh] = useState(null);
  const [hoveredMesh, setHoveredMesh] = useState(null);
  const [meshInventory, setMeshInventory] = useState([]);

  // Modo Debug: mientras el modelo no venga limpio ni separado a mano en
  // Blender, esto es lo que permite descubrir los nombres crudos de cada
  // malla (node_3, Object_14...) directamente desde el navegador. Empieza
  // activo porque es justo lo que se necesita al recibir un modelo nuevo.
  const [debugMode, setDebugMode] = useState(true);
  const [debugSelectedMesh, setDebugSelectedMesh] = useState(null);

  const handleHoverChange = useCallback((meshName) => {
    setHoveredMesh(meshName);
  }, []);

  const handleMeshNames = useCallback((inventory) => {
    setMeshInventory(inventory);
  }, []);

  const handleSelect = useCallback(
    (meshName) => {
      if (debugMode) {
        // eslint-disable-next-line no-console
        console.log("[Modo Debug] malla seleccionada:", meshName);
        setDebugSelectedMesh(meshName);
        return;
      }
      setSelectedMesh(meshName);
    },
    [debugMode]
  );

  const handleClose = useCallback(() => setSelectedMesh(null), []);

  const selectedStructure = selectedMesh
    ? findStructureByMeshName(selectedMesh, estructuras)
    : null;

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

        <button
          type="button"
          onClick={() => setDebugMode((prev) => !prev)}
          className={`pointer-events-auto rounded-md border px-3 py-1.5 text-xs font-semibold transition ${
            debugMode
              ? "border-amber-400 bg-amber-500 text-slate-900 hover:bg-amber-400"
              : "border-slate-600 bg-slate-800 text-slate-200 hover:bg-slate-700"
          }`}
        >
          {debugMode ? "Modo Debug: ACTIVO" : "Modo Debug: inactivo"}
        </button>
      </header>

      <ModelErrorBoundary fallback={<NoModelFallback />}>
        <Scene
          modelUrl={MODEL_URL}
          onSelect={handleSelect}
          onHoverChange={handleHoverChange}
          onMeshNames={handleMeshNames}
        />
      </ModelErrorBoundary>

      {debugMode ? (
        <DebugPanel
          hoveredMesh={hoveredMesh}
          selectedMesh={debugSelectedMesh}
          meshInventory={meshInventory}
        />
      ) : null}

      {!debugMode && selectedMesh ? (
        <InfoPanel structure={selectedStructure} meshName={selectedMesh} onClose={handleClose} />
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
