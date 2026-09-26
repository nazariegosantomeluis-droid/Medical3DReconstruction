export default function DebugPanel({ hoveredMesh, selectedMesh, meshInventory }) {
  return (
    <aside
      role="complementary"
      aria-label="Panel de depuración de mallas"
      className="fixed bottom-4 left-4 z-20 flex max-h-[70vh] w-80 flex-col overflow-hidden
                 rounded-lg border border-amber-500/40 bg-slate-950/95 shadow-2xl"
    >
      <div className="border-b border-amber-500/30 bg-amber-500/10 px-4 py-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-amber-400">
          Modo Debug — nombres originales de malla
        </p>
      </div>

      <div className="space-y-2 border-b border-slate-800 px-4 py-3 font-mono text-xs">
        <Fila etiqueta="Bajo el cursor" valor={hoveredMesh} acento />
        <Fila etiqueta="Última seleccionada (clic)" valor={selectedMesh} />
      </div>

      <p className="px-4 pb-1 pt-3 text-xs font-semibold text-slate-400">
        Mallas detectadas en el modelo ({meshInventory.length})
      </p>

      <ul className="flex-1 space-y-1 overflow-y-auto px-4 pb-3 font-mono text-xs text-slate-300">
        {meshInventory.map(({ name, count }) => {
          const isActive = name === hoveredMesh || name === selectedMesh;
          return (
            <li
              key={name || "(sin nombre)"}
              className={`rounded px-1.5 py-0.5 ${isActive ? "bg-amber-500/20 text-amber-300" : ""}`}
            >
              {name || "(sin nombre)"}
              {count > 1 ? <span className="text-slate-500"> ×{count}</span> : null}
            </li>
          );
        })}
      </ul>
    </aside>
  );
}

function Fila({ etiqueta, valor, acento }) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <span className="text-slate-500">{etiqueta}:</span>
      <span className={acento ? "text-sky-400" : "text-slate-200"}>{valor || "—"}</span>
    </div>
  );
}
