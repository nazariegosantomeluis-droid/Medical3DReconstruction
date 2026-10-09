import { motion } from "framer-motion";

const SISTEMA_LABELS = {
  respiratorio: "Sistema respiratorio",
  cardiovascular: "Sistema cardiovascular",
  reconstruccion_propia: "Mi reconstrucción 3D",
};

// Lista siempre visible en la barra lateral, no un desplegable flotante —
// es el punto de entrada explícito a las 32 estructuras y temas del Cuadro
// de Conocimiento, incluidos los que no tienen malla propia (estructuras
// microscópicas/no modeladas y temas de fisiología general, como el
// sistema de conducción eléctrica o los volúmenes pulmonares) que de otro
// modo solo se alcanzarían de rebote desde un chip de "estructuras
// relacionadas".
export default function StructureIndex({ structures, selectedId, onSelect }) {
  const porSistema = structures.reduce((acc, s) => {
    (acc[s.sistema] ??= []).push(s);
    return acc;
  }, {});

  return (
    <div className="space-y-5">
      {Object.entries(porSistema).map(([sistema, items]) => (
        <div key={sistema}>
          <p className="mb-1.5 flex items-center gap-1.5 px-1 text-[0.68rem] font-semibold uppercase tracking-wider text-ink-faint">
            <SistemaIcon sistema={sistema} />
            {SISTEMA_LABELS[sistema] ?? sistema}
          </p>
          <ul className="space-y-0.5">
            {items.map((s) => {
              const active = s.id === selectedId;
              return (
                <li key={s.id} className="relative">
                  <button
                    type="button"
                    onClick={() => onSelect(s.id)}
                    aria-pressed={active}
                    className={`relative flex w-full items-center justify-between rounded-md px-2.5 py-1.5 text-left text-[0.82rem] transition-colors ${
                      active ? "text-ink" : "text-ink-dim hover:bg-surface-raised hover:text-ink"
                    }`}
                  >
                    {active ? (
                      <motion.span
                        layoutId="structure-index-active"
                        className="absolute inset-0 rounded-md bg-accent-soft ring-1 ring-inset ring-accent/30"
                        transition={{ type: "spring", stiffness: 500, damping: 38 }}
                      />
                    ) : null}
                    <span className="relative flex items-center gap-2">
                      <span
                        className={`h-1.5 w-1.5 shrink-0 rounded-full transition-colors ${
                          active ? "bg-accent-strong shadow-glow-accent-sm" : "bg-border"
                        }`}
                        aria-hidden="true"
                      />
                      {s.nombre}
                    </span>
                    {s.fichaTecnica ? (
                      <span className="relative shrink-0 rounded-full border border-accent/40 px-1.5 py-0.5 text-[0.58rem] font-bold uppercase tracking-wider text-accent-strong">
                        propio
                      </span>
                    ) : s.sinMalla ? (
                      <span className="relative shrink-0 text-[0.62rem] text-ink-faint">sin malla</span>
                    ) : null}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </div>
  );
}

function SistemaIcon({ sistema }) {
  if (sistema === "reconstruccion_propia") {
    return (
      <svg viewBox="0 0 24 24" className="h-3 w-3 text-accent-strong" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
        <rect x="3" y="4" width="18" height="13" rx="1.5" />
        <path d="M3 13h18" strokeLinecap="round" />
        <path d="M8 20h8" strokeLinecap="round" />
        <path d="M12 17v3" strokeLinecap="round" />
        <circle cx="12" cy="8.5" r="2.2" />
      </svg>
    );
  }
  if (sistema === "respiratorio") {
    return (
      <svg viewBox="0 0 24 24" className="h-3 w-3 text-ink-faint" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
        <path d="M12 3v7" strokeLinecap="round" />
        <path d="M12 10c-1.5 0-2.5 1.4-2.5 3.2 0 2.6-1.2 4.3-3 4.3-1.8 0-2.5-1.4-2.5-2.8" strokeLinecap="round" />
        <path d="M12 10c1.5 0 2.5 1.4 2.5 3.2 0 2.6 1.2 4.3 3 4.3 1.8 0 2.5-1.4 2.5-2.8" strokeLinecap="round" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" className="h-3 w-3 text-ink-faint" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <path
        d="M12 20.2s-7.5-4.6-9.6-9.1C1.1 7.9 2.7 4.8 5.8 4.2c2-.4 3.9.6 5 2.3 1.1-1.7 3-2.7 5-2.3 3.1.6 4.7 3.7 3.4 6.9-2.1 4.5-9.2 9.1-9.2 9.1Z"
        strokeLinejoin="round"
      />
      <path d="M4.5 11h3l1.5-2.5L11 13l1.5-4 1.5 2h4.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
