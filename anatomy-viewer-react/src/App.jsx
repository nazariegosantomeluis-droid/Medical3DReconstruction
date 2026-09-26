import { useCallback, useState } from "react";
import Scene from "./components/Scene";
import InfoPanel from "./components/InfoPanel";
import estructuras from "./data/estructuras.json";
import { findStructureByMeshName } from "./utils/matchStructure";

// Cambia esto por el nombre real de tu archivo dentro de public/models/.
const MODEL_URL = "/models/sistema-cardiorrespiratorio.glb";

export default function App() {
  const [selectedMesh, setSelectedMesh] = useState(null);
  const [hoveredMesh, setHoveredMesh] = useState(null);

  const handleSelect = useCallback((meshName) => {
    setSelectedMesh(meshName);
  }, []);

  const handleClose = useCallback(() => setSelectedMesh(null), []);

  const selectedStructure = selectedMesh
    ? findStructureByMeshName(selectedMesh, estructuras)
    : null;

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-slate-900">
      <header className="pointer-events-none absolute top-0 left-0 z-10 p-4">
        <h1 className="text-lg font-semibold text-white drop-shadow">
          Visor anatómico cardiorrespiratorio
        </h1>
        <p className="mt-1 text-xs text-slate-300">
          {hoveredMesh
            ? `Estructura bajo el cursor: ${hoveredMesh}`
            : "Arrastra para rotar · rueda para hacer zoom · clic para más información"}
        </p>
      </header>

      <Scene modelUrl={MODEL_URL} onSelect={handleSelect} onHoverChange={setHoveredMesh} />

      {selectedMesh ? (
        <InfoPanel structure={selectedStructure} meshName={selectedMesh} onClose={handleClose} />
      ) : null}
    </div>
  );
}
