export default function InfoPanel({ structure, meshName, allStructures, onClose, onSelectRelated }) {
  const nombre = structure?.nombre ?? meshName;

  return (
    <aside
      role="dialog"
      aria-label={`Información de ${nombre}`}
      className="fixed top-0 right-0 z-20 h-full w-full overflow-y-auto border-l
                 border-border bg-surface shadow-2xl sm:w-[26rem]"
    >
      <div className="flex items-center justify-between border-b border-border bg-surface-raised px-6 py-4">
        <h2 className="text-lg font-semibold text-ink">{nombre}</h2>
        <button
          type="button"
          onClick={onClose}
          aria-label="Cerrar panel de información"
          className="rounded-full p-1.5 text-ink-faint transition hover:bg-border/60 hover:text-ink"
        >
          <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path strokeLinecap="round" d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>
      </div>

      {!structure ? (
        <div className="p-6 text-sm text-ink-dim">
          Esta malla (<code className="rounded bg-surface-raised px-1 py-0.5 text-ink">{meshName}</code>)
          todavía no tiene datos asociados. Agrégala en{" "}
          <code className="rounded bg-surface-raised px-1 py-0.5 text-ink">
            src/data/estructuras.json
          </code>
          , ya sea como <code className="rounded bg-surface-raised px-1 py-0.5 text-ink">id</code> o
          dentro de <code className="rounded bg-surface-raised px-1 py-0.5 text-ink">meshNames</code>.
        </div>
      ) : (
        <div className="space-y-6 p-6">
          {structure.imagenUrl ? (
            <img
              src={structure.imagenUrl}
              alt={nombre}
              className="h-40 w-full rounded-lg border border-border object-cover"
            />
          ) : null}

          {structure.notaSinMalla ? (
            <p className="rounded-md border border-warn/30 bg-warn/10 px-3 py-2 text-xs text-warn">
              {structure.notaSinMalla}
            </p>
          ) : null}

          {structure.notaEspecimen ? (
            <p className="rounded-md border border-accent/30 bg-accent-soft px-3 py-2 text-xs text-accent-ink">
              {structure.notaEspecimen}
            </p>
          ) : null}

          <CuadroDeConocimiento structure={structure} />

          <ConexionesClinicas
            structure={structure}
            allStructures={allStructures}
            onSelectRelated={onSelectRelated}
          />
        </div>
      )}
    </aside>
  );
}

// Su propio apartado, con nombre y borde propios — no son solo párrafos
// sueltos debajo del título de la estructura, son el "Cuadro de
// Conocimiento": previo / nuevo / aplicación clínica, como bloque.
function CuadroDeConocimiento({ structure }) {
  return (
    <div className="rounded-lg border border-border bg-surface-raised/60 p-4">
      <h3 className="mb-3 text-[0.68rem] font-bold uppercase tracking-wider text-ink-faint">
        Cuadro de Conocimiento
      </h3>
      <div className="space-y-4">
        <Seccion titulo="Lo que sabía previamente" texto={structure.conocimientoPrevio} />
        <Seccion titulo="Lo que sé después de estudiar" texto={structure.conocimientoNuevo} />
        <Seccion titulo="Aplicación clínica" texto={structure.aplicacionClinica} />
      </div>
    </div>
  );
}

function Seccion({ titulo, texto }) {
  return (
    <div>
      <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-accent-strong">
        {titulo}
      </h4>
      <p className="text-sm leading-relaxed text-ink-dim">
        {texto || <span className="italic text-ink-faint">Pendiente de completar.</span>}
      </p>
    </div>
  );
}

// El "mapa de conexiones clínicas": en vez de una ficha aislada, cada
// estructura enlaza a las que están anatómica o fisiológicamente conectadas
// a ella, para que el estudio se parezca más a navegar un grafo que a leer
// una tarjeta suelta. Un chip sin malla propia (p. ej. "Pericardio") sigue
// siendo navegable, solo que no hay nada que mostrar en el modelo 3D.
function ConexionesClinicas({ structure, allStructures, onSelectRelated }) {
  const relacionadas = (structure.relacionadas ?? [])
    .map((id) => allStructures?.find((s) => s.id === id))
    .filter(Boolean);

  if (relacionadas.length === 0) return null;

  return (
    <div className="border-t border-border pt-5">
      <h3 className="mb-2.5 text-[0.68rem] font-bold uppercase tracking-wider text-ink-faint">
        Estructuras relacionadas
      </h3>
      <div className="flex flex-wrap gap-1.5">
        {relacionadas.map((rel) => (
          <button
            key={rel.id}
            type="button"
            onClick={() => onSelectRelated(rel.id)}
            title={rel.sinMalla ? "Esta estructura aún no tiene malla 3D propia" : undefined}
            className={`rounded-full border px-2.5 py-1 text-xs font-medium transition ${
              rel.sinMalla
                ? "border-dashed border-border text-ink-faint hover:bg-surface-raised"
                : "border-accent/30 bg-accent-soft text-accent-ink hover:bg-accent/25"
            }`}
          >
            {rel.nombre}
          </button>
        ))}
      </div>
    </div>
  );
}
