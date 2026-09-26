export default function InfoPanel({ structure, meshName, onClose }) {
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

          <Seccion titulo="Lo que sabía previamente" texto={structure.conocimientoPrevio} />
          <Seccion titulo="Lo que sé después de estudiar" texto={structure.conocimientoNuevo} />
          <Seccion titulo="Aplicación clínica" texto={structure.aplicacionClinica} />
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
