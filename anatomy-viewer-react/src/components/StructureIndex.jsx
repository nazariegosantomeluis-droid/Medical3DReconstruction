// Lista siempre visible en la barra lateral, no un desplegable flotante —
// es el punto de entrada explícito a las 23 estructuras, incluidas las 4
// sin malla propia que de otro modo solo se alcanzarían de rebote desde un
// chip de "estructuras relacionadas".
export default function StructureIndex({ structures, selectedId, onSelect }) {
  const porSistema = structures.reduce((acc, s) => {
    (acc[s.sistema] ??= []).push(s);
    return acc;
  }, {});

  return (
    <div className="space-y-4">
      {Object.entries(porSistema).map(([sistema, items]) => (
        <div key={sistema}>
          <p className="mb-1.5 px-1 text-[0.68rem] font-semibold uppercase tracking-wider text-ink-faint">
            {sistema === "respiratorio" ? "Sistema respiratorio" : "Sistema cardiovascular"}
          </p>
          <ul className="space-y-0.5">
            {items.map((s) => {
              const active = s.id === selectedId;
              return (
                <li key={s.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(s.id)}
                    aria-pressed={active}
                    className={`flex w-full items-center justify-between rounded-md px-2.5 py-1.5 text-left text-[0.82rem] transition ${
                      active
                        ? "bg-accent-soft text-ink"
                        : "text-ink-dim hover:bg-surface-raised hover:text-ink"
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      <span
                        className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                          active ? "bg-accent-strong" : "bg-border"
                        }`}
                        aria-hidden="true"
                      />
                      {s.nombre}
                    </span>
                    {s.sinMalla ? (
                      <span className="shrink-0 text-[0.62rem] text-ink-faint">sin malla</span>
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
