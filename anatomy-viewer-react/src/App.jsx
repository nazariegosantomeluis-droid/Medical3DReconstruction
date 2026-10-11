import { useCallback, useMemo, useState } from "react";
import { Loader } from "@react-three/drei";
import { AnimatePresence, motion } from "framer-motion";
import Scene from "./components/Scene";
import InfoPanel from "./components/InfoPanel";
import DebugPanel from "./components/DebugPanel";
import StructureIndex from "./components/StructureIndex";
import ModelErrorBoundary from "./components/ModelErrorBoundary";
import estructuras from "./data/estructuras.json";
import { findStructureByMeshName } from "./utils/matchStructure";
import { GROUP_NODE_NAMES, DEFAULT_GROUP } from "./constants/modelGroups";

const GROUP_LABELS = {
  atlas_bodyparts3d: "Piezas internas",
  especimen_real: "Corazón completo",
  reconstruccion_propia: "Mi reconstrucción",
};
const GROUP_SUBLABELS = {
  atlas_bodyparts3d: "Atlas BodyParts3D",
  especimen_real: "Espécimen ex-vivo real",
  reconstruccion_propia: "Pulmón y corazón · TC real propia",
};

// Cambia esto por el nombre real de tu archivo dentro de public/models/.
// Se arma sobre BASE_URL (en vez de un "/models/..." fijo) para que el
// modelo se siga encontrando cuando el sitio se publique bajo una subruta,
// como /anatomy-viewer/, y no solo en la raíz del dominio.
const MODEL_URL = `${import.meta.env.BASE_URL}models/corazon-segmentado.glb`;

// Deep-link para el código QR del Cuadro de Conocimiento: visitar
// /anatomy-viewer/?ver=mi-reconstruccion abre directo el panel del pulmón
// propio con el grupo correcto activo, sin que quien escanea el QR tenga
// que saber en qué botón hacer clic.
const DEEP_LINK_PARAM = "ver";
const DEEP_LINK_OWN_RECONSTRUCTION = "mi-reconstruccion";
const OWN_RECONSTRUCTION_ID = "pulmon_reconstruccion_propia";

function readDeepLinkTarget() {
  if (typeof window === "undefined") return null;
  return new URLSearchParams(window.location.search).get(DEEP_LINK_PARAM);
}

export default function App() {
  const [hoveredMesh, setHoveredMesh] = useState(null);
  const [meshInventory, setMeshInventory] = useState([]);

  // Modo Debug: reporta el nombre crudo de cualquier malla bajo el cursor o
  // clickeada, sin abrir el Cuadro de Conocimiento — solo para diagnosticar
  // un .glb nuevo. Apagado por defecto: la experiencia normal es el mapa de
  // conexiones de abajo.
  const [debugMode, setDebugMode] = useState(false);
  const [debugSelectedMesh, setDebugSelectedMesh] = useState(null);

  // Por debajo del breakpoint `sm`, la barra lateral es un cajón (drawer)
  // que se abre por encima del visor en vez de robarle casi todo el ancho
  // de pantalla a un celular — crítico porque el código QR del Cuadro de
  // Conocimiento manda justo a este visor, en un teléfono.
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  const isOwnReconstructionDeepLink = useMemo(
    () => readDeepLinkTarget() === DEEP_LINK_OWN_RECONSTRUCTION,
    []
  );

  // Selección real (no-debug): o una estructura conocida (selectedId), o una
  // malla cruda que no matcheó ninguna estructura (unmatchedMesh) — nunca
  // las dos a la vez.
  const [selectedId, setSelectedId] = useState(
    isOwnReconstructionDeepLink ? OWN_RECONSTRUCTION_ID : null
  );
  const [unmatchedMesh, setUnmatchedMesh] = useState(null);

  // El .glb trae tres especímenes reales que no comparten coordenadas: el
  // corazón completo (ex-vivo), las piezas internas del atlas BodyParts3D, y
  // el pulmón de la reconstrucción propia. Solo uno está visible a la vez;
  // seleccionar una estructura del otro grupo cambia esto y hace que la
  // cámara se reencuadre a él (ver Model.jsx).
  const [activeGroup, setActiveGroup] = useState(
    isOwnReconstructionDeepLink ? "reconstruccion_propia" : DEFAULT_GROUP
  );

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

  // El selector de grupo en la cabecera de la barra lateral cambia de
  // espécimen directamente, sin pasar por una estructura — hay que limpiar
  // la selección activa, porque si no, Model.jsx seguiría intentando
  // resaltar una malla que ya no pertenece al grupo recién activado (y, al
  // no encontrarla ahí, ocultaría todo el grupo nuevo por completo).
  const handleSwitchGroup = useCallback((group) => {
    setActiveGroup(group);
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
    <div className="relative flex h-screen w-screen overflow-hidden bg-bg font-sans text-ink">
      {/* Atmósfera de fondo: dos manchas de luz muy difusas y lentas, en los
          colores de la marca, que le dan profundidad al visor sin competir
          con el modelo — se ven incluso a través del canvas transparente. */}
      <div aria-hidden="true" className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
        <div className="absolute -left-40 -top-40 h-[32rem] w-[32rem] animate-drift rounded-full bg-accent/20 blur-[120px]" />
        <div className="absolute -right-32 bottom-0 h-[28rem] w-[28rem] animate-drift-slow rounded-full bg-sky-500/10 blur-[120px]" />
      </div>

      {/* Fondo que cierra el cajón al tocar afuera — solo existe en
          pantallas angostas, mientras el cajón está abierto. */}
      <AnimatePresence>
        {mobileSidebarOpen ? (
          <motion.div
            key="mobile-sidebar-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setMobileSidebarOpen(false)}
            className="fixed inset-0 z-[25] bg-black/60 sm:hidden"
            aria-hidden="true"
          />
        ) : null}
      </AnimatePresence>

      <Sidebar
        debugMode={debugMode}
        onToggleDebug={() => setDebugMode((prev) => !prev)}
        activeGroup={activeGroup}
        onSwitchGroup={(group) => {
          handleSwitchGroup(group);
          setMobileSidebarOpen(false);
        }}
        selectedId={selectedId}
        onSelect={(id) => {
          handleSelectRelated(id);
          setMobileSidebarOpen(false);
        }}
        mobileOpen={mobileSidebarOpen}
        onCloseMobile={() => setMobileSidebarOpen(false)}
      />

      <main className="relative z-10 flex-1 overflow-hidden">
        <div className="pointer-events-none absolute left-5 top-5 z-10 flex max-w-[calc(100%-2.5rem)] items-center gap-2 sm:max-w-sm">
          <button
            type="button"
            onClick={() => setMobileSidebarOpen((prev) => !prev)}
            aria-label="Abrir índice de estructuras"
            className="glass-panel pointer-events-auto flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-white/5 text-ink-dim shadow-glass sm:hidden"
          >
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
              <path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" />
            </svg>
          </button>
          <p
            className={`glass-panel inline-flex min-w-0 items-center gap-2 truncate rounded-full border px-3.5 py-1.5 text-xs shadow-glass transition-colors ${
              hoveredMesh ? "border-accent/40 text-accent-ink" : "border-white/5 text-ink-dim"
            }`}
          >
            <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${hoveredMesh ? "bg-accent-strong" : "bg-ink-faint"}`} />
            <span className="truncate">
              {hoveredMesh
                ? `Estructura bajo el cursor: ${hoveredMesh}`
                : "Arrastra para rotar · rueda para hacer zoom · clic para más información"}
            </span>
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
          containerStyles={{ background: "rgba(15,16,18,0.92)", backdropFilter: "blur(6px)" }}
          innerStyles={{ width: "14rem", height: "3px", background: "#35373b", borderRadius: "999px" }}
          barStyles={{ background: "linear-gradient(90deg, #a5434b, #f3a9a0)", borderRadius: "999px" }}
          dataStyles={{
            color: "#9a9da2",
            fontFamily: "'Space Grotesk', Inter, sans-serif",
            fontSize: "0.75rem",
            marginTop: "0.75rem",
            letterSpacing: "0.02em",
          }}
          dataInterpolation={(p) => `Cargando modelo… ${p.toFixed(0)}%`}
        />

        <AnimatePresence>
          {debugMode ? (
            <DebugPanel
              hoveredMesh={hoveredMesh}
              selectedMesh={debugSelectedMesh}
              meshInventory={meshInventory}
            />
          ) : null}
        </AnimatePresence>

        <AnimatePresence>
          {panelOpen ? (
            <InfoPanel
              structure={selectedStructure}
              meshName={unmatchedMesh}
              allStructures={estructuras}
              onClose={handleClose}
              onSelectRelated={handleSelectRelated}
            />
          ) : null}
        </AnimatePresence>

        {meshInventory.length > 0 ? (
          <footer className="glass-panel pointer-events-none absolute bottom-3 right-4 z-10 max-w-xs rounded-lg border border-white/5 px-3 py-2 text-right text-[0.62rem] leading-snug text-ink-faint shadow-glass">
            Piezas internas: BodyParts3D/Anatomography, © Database Center for Life Science (DBCLS) —
            CC BY-SA 2.1 Japan. Corazón completo: espécimen ex-vivo real (LADAF-2021-17, micro-CT
            sincrotrón).
          </footer>
        ) : null}
      </main>
    </div>
  );
}

function Sidebar({ debugMode, onToggleDebug, activeGroup, onSwitchGroup, selectedId, onSelect, mobileOpen, onCloseMobile }) {
  return (
    <aside
      className={`glass-panel fixed inset-y-0 left-0 z-30 flex w-80 shrink-0 flex-col border-r
                  border-white/5 shadow-glass transition-transform duration-300 ease-out
                  sm:relative sm:z-10 sm:translate-x-0 ${mobileOpen ? "translate-x-0" : "-translate-x-full"}`}
    >
      <div className="flex items-center gap-2.5 border-b border-white/5 px-4 py-4">
        <span className="relative flex h-8 w-8 shrink-0 items-center justify-center">
          <span className="absolute inset-0 animate-pulse-slow rounded-full bg-accent/30 blur-md" aria-hidden="true" />
          <svg
            className="relative h-5 w-5 text-accent-strong"
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
        </span>
        <div className="min-w-0 flex-1">
          <h1 className="truncate font-display text-sm font-semibold tracking-tight text-ink">
            Visor cardiorrespiratorio
          </h1>
          <p className="truncate text-[0.68rem] text-ink-faint">Mapa de conexiones clínicas</p>
        </div>
        <button
          type="button"
          onClick={onCloseMobile}
          aria-label="Cerrar índice de estructuras"
          className="shrink-0 rounded-full p-1.5 text-ink-faint transition hover:bg-border/60 hover:text-ink sm:hidden"
        >
          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path strokeLinecap="round" d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>
      </div>

      <div className="border-b border-white/5 px-4 py-3">
        <p className="mb-2 text-[0.68rem] font-semibold uppercase tracking-wider text-ink-faint">
          Espécimen
        </p>
        <GroupSwitch activeGroup={activeGroup} onSwitchGroup={onSwitchGroup} />
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4" aria-label="Índice de estructuras">
        <StructureIndex structures={estructuras} selectedId={selectedId} onSelect={onSelect} />
      </nav>

      <div className="border-t border-white/5 px-4 py-3">
        <button
          type="button"
          onClick={onToggleDebug}
          className={`w-full rounded-md border px-3 py-1.5 text-xs font-semibold transition-all ${
            debugMode
              ? "border-warn bg-warn/20 text-warn shadow-[0_0_16px_-4px_rgba(201,151,74,0.6)]"
              : "border-border bg-surface-raised text-ink-dim hover:border-ink-faint/40 hover:text-ink"
          }`}
        >
          {debugMode ? "Modo Debug: ACTIVO" : "Modo Debug"}
        </button>
      </div>
    </aside>
  );
}

// Toggle de dos opciones con una píldora que se desliza al estado activo —
// cambia de espécimen directamente desde la cabecera, sin tener que
// seleccionar primero una estructura que viva en el otro grupo.
function GroupSwitch({ activeGroup, onSwitchGroup }) {
  const groups = Object.keys(GROUP_LABELS);
  return (
    <div className="relative flex flex-col gap-1 rounded-lg bg-surface-raised/80 p-1">
      {groups.map((group) => {
        const active = group === activeGroup;
        const isOwnWork = group === "reconstruccion_propia";
        return (
          <button
            key={group}
            type="button"
            onClick={() => onSwitchGroup(group)}
            aria-pressed={active}
            className="relative flex items-center justify-between rounded-md px-2.5 py-1.5 text-left outline-none"
          >
            {active ? (
              <motion.span
                layoutId="group-switch-pill"
                className="absolute inset-0 rounded-md bg-accent/90 shadow-glow-accent-sm"
                transition={{ type: "spring", stiffness: 420, damping: 32 }}
              />
            ) : null}
            <span className="relative min-w-0">
              <span
                className={`block truncate text-[0.72rem] font-semibold leading-tight ${
                  active ? "text-white" : "text-ink-dim"
                }`}
              >
                {GROUP_LABELS[group]}
              </span>
              <span
                className={`block truncate text-[0.6rem] leading-tight ${
                  active ? "text-white/80" : "text-ink-faint"
                }`}
              >
                {GROUP_SUBLABELS[group]}
              </span>
            </span>
            {isOwnWork ? (
              <span
                className={`relative ml-2 shrink-0 rounded-full border px-1.5 py-0.5 text-[0.56rem] font-bold uppercase tracking-wider ${
                  active ? "border-white/40 text-white" : "border-accent/40 text-accent-strong"
                }`}
              >
                propio
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
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
