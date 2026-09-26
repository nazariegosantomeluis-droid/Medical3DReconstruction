export default function InfoPanel({ structure, meshName, allStructures, onClose, onSelectRelated }) {
  const nombre = structure?.nombre ?? meshName;

  return (
    <aside
      role="dialog"
      aria-label={`Información de ${nombre}`}
      className="fixed top-0 right-0 z-20 h-full w-full overflow-y-auto border-l
                 border-slate-200 bg-white shadow-2xl sm:w-96"
    >
      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-5 py-4">
        <h2 className="text-lg font-semibold text-slate-900">{nombre}</h2>
        <button
          type="button"
          onClick={onClose}
          aria-label="Cerrar panel de información"
          className="rounded-full p-1.5 text-slate-500 transition hover:bg-slate-200 hover:text-slate-900"
        >
          <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path strokeLinecap="round" d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>
      </div>

      {!structure ? (
        <div className="p-5 text-sm text-slate-600">
          Esta malla (<code className="rounded bg-slate-100 px-1 py-0.5">{meshName}</code>) todavía no
          tiene datos asociados. Agrégala en{" "}
          <code className="rounded bg-slate-100 px-1 py-0.5">src/data/estructuras.json</code>, ya sea
          como <code className="rounded bg-slate-100 px-1 py-0.5">id</code> o dentro de{" "}
          <code className="rounded bg-slate-100 px-1 py-0.5">meshNames</code>.
        </div>
      ) : (
        <div className="space-y-5 p-5">
          {structure.imagenUrl ? (
            <img
              src={structure.imagenUrl}
              alt={nombre}
              className="h-40 w-full rounded-lg border border-slate-200 object-cover"
            />
          ) : null}

          {structure.notaSinMalla ? (
            <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              {structure.notaSinMalla}
            </p>
          ) : null}

          {structure.notaEspecimen ? (
            <p className="rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-xs text-sky-800">
              {structure.notaEspecimen}
            </p>
          ) : null}

          <Seccion titulo="Lo que sabía previamente" texto={structure.conocimientoPrevio} />
          <Seccion titulo="Lo que sé después de estudiar" texto={structure.conocimientoNuevo} />
          <Seccion titulo="Aplicación clínica" texto={structure.aplicacionClinica} />

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

function Seccion({ titulo, texto }) {
  return (
    <div>
      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-sky-600">{titulo}</h3>
      <p className="text-sm leading-relaxed text-slate-700">
        {texto || <span className="italic text-slate-400">Pendiente de completar.</span>}
      </p>
    </div>
  );
}

// El "mapa de conexiones clínicas": en vez de una ficha aislada, cada
// estructura enlaza a las que están anatómica o fisiológicamente conectadas
// a ella, para que el estudio se parezca más a navegar un grafo que a leer
// una tarjeta suelta. Un chip sin malla propia (p. ej. "Corazón" como nodo
// resumen) sigue siendo navegable, solo que no resalta nada en el modelo 3D.
function ConexionesClinicas({ structure, allStructures, onSelectRelated }) {
  const relacionadas = (structure.relacionadas ?? [])
    .map((id) => allStructures?.find((s) => s.id === id))
    .filter(Boolean);

  if (relacionadas.length === 0) return null;

  return (
    <div className="border-t border-slate-100 pt-4">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-sky-600">
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
                ? "border-dashed border-slate-300 text-slate-500 hover:bg-slate-50"
                : "border-sky-200 bg-sky-50 text-sky-700 hover:bg-sky-100"
            }`}
          >
            {rel.nombre}
          </button>
        ))}
      </div>
    </div>
  );
}
