import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const SISTEMA_LABELS = {
  respiratorio: "Sistema respiratorio",
  cardiovascular: "Sistema cardiovascular",
  reconstruccion_propia: "Mi reconstrucción 3D",
};

// Secciones que arrancan colapsadas — cardiovascular y respiratorio ahora
// incluyen, además de las estructuras del visor, todos los temas de la
// guía de alto rendimiento (ya no viven en su propia categoría aparte:
// son más contenido del Cuadro de Conocimiento de cada sistema), así que
// cada una pasó de ~20 a 30-45 entradas. Mostrarlas siempre abiertas
// enterraría el índice bajo una lista kilométrica. "Mi reconstrucción 3D"
// arranca abierta porque son solo 2 piezas.
const COLLAPSED_BY_DEFAULT = new Set(["cardiovascular", "respiratorio"]);

// Agrupar visualmente por número mayor ("1", "2"...) ayuda a escanear una
// lista larga sin perderse — no es otro nivel de colapsable, solo un
// sub-encabezado liviano entre tandas. Solo los temas que vienen de la
// guía traen ese número al inicio del nombre; el resto de las estructuras
// (sin número) simplemente no dispara ningún encabezado.
function majorGroupOf(nombre) {
  const m = /^(\d+)(?:\.\d+)?/.exec(nombre);
  return m ? m[1] : null;
}

// Lista siempre visible en la barra lateral, no un desplegable flotante —
// es el punto de entrada explícito a las estructuras y temas del Cuadro
// de Conocimiento y de la Guía de Alto Rendimiento, incluidos los que no
// tienen malla propia (estructuras microscópicas/no modeladas, temas de
// fisiología general, y referencia de examen) que de otro modo solo se
// alcanzarían de rebote desde un chip de "estructuras relacionadas".
export default function StructureIndex({ structures, selectedId, onSelect }) {
  const porSistema = structures.reduce((acc, s) => {
    (acc[s.sistema] ??= []).push(s);
    return acc;
  }, {});

  const [collapsed, setCollapsed] = useState(COLLAPSED_BY_DEFAULT);
  const toggle = (sistema) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(sistema)) next.delete(sistema);
      else next.add(sistema);
      return next;
    });
  };

  return (
    <div className="space-y-5">
      {Object.entries(porSistema).map(([sistema, items]) => {
        const isOpen = !collapsed.has(sistema);
        let lastMajorGroup = null;
        return (
          <div key={sistema}>
            <button
              type="button"
              onClick={() => toggle(sistema)}
              aria-expanded={isOpen}
              className="mb-1.5 flex w-full items-center gap-1.5 px-1 text-[0.68rem] font-semibold uppercase tracking-wider text-ink-faint transition-colors hover:text-ink-dim"
            >
              <SistemaIcon sistema={sistema} />
              <span className="flex-1 text-left">{SISTEMA_LABELS[sistema] ?? sistema}</span>
              <span className="text-[0.6rem] font-normal normal-case text-ink-faint">{items.length}</span>
              <motion.svg
                viewBox="0 0 24 24"
                className="h-3 w-3 shrink-0"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                animate={{ rotate: isOpen ? 90 : 0 }}
                transition={{ duration: 0.18 }}
                aria-hidden="true"
              >
                <path d="M9 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
              </motion.svg>
            </button>
            <AnimatePresence initial={false}>
              {isOpen ? (
                <motion.ul
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2, ease: "easeOut" }}
                  className="space-y-0.5 overflow-hidden"
                >
                  {items.map((s) => {
                    const active = s.id === selectedId;
                    const group = majorGroupOf(s.nombre);
                    const showGroupLabel = group && group !== lastMajorGroup;
                    if (showGroupLabel) lastMajorGroup = group;
                    return (
                      <li key={s.id} className="relative">
                        {showGroupLabel ? (
                          <p className="mb-0.5 mt-2.5 px-2.5 text-[0.6rem] font-semibold uppercase tracking-wide text-ink-faint/70 first:mt-0">
                            Bloque {group}
                          </p>
                        ) : null}
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
                          <span className="relative flex min-w-0 items-center gap-2">
                            <span
                              className={`h-1.5 w-1.5 shrink-0 rounded-full transition-colors ${
                                active ? "bg-accent-strong shadow-glow-accent-sm" : "bg-border"
                              }`}
                              aria-hidden="true"
                            />
                            <span className="truncate">{s.nombre}</span>
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
                </motion.ul>
              ) : null}
            </AnimatePresence>
          </div>
        );
      })}
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
