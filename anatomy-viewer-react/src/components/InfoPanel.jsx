import { motion } from "framer-motion";

export default function InfoPanel({ structure, meshName, allStructures, onClose, onSelectRelated }) {
  const nombre = structure?.nombre ?? meshName;

  return (
    <motion.aside
      role="dialog"
      aria-label={`Información de ${nombre}`}
      initial={{ x: 32, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 32, opacity: 0 }}
      transition={{ type: "spring", stiffness: 340, damping: 34 }}
      className="glass-panel fixed top-0 right-0 z-20 h-full w-full overflow-y-auto border-l
                 border-white/5 shadow-glass sm:w-[26rem]"
    >
      <div className="sticky top-0 z-10 flex items-center justify-between border-b border-white/5 bg-surface-raised/80 px-6 py-4 backdrop-blur">
        <h2 className="font-display text-lg font-semibold tracking-tight text-ink">{nombre}</h2>
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
        <motion.div
          key={structure.id}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: "easeOut" }}
          className="space-y-6 p-6"
        >
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

          {structure.fichaTecnica ? <FichaTecnica ficha={structure.fichaTecnica} /> : null}

          <CuadroDeConocimiento structure={structure} />

          <ConexionesClinicas
            structure={structure}
            allStructures={allStructures}
            onSelectRelated={onSelectRelated}
          />
        </motion.div>
      )}
    </motion.aside>
  );
}

// Grilla de datos duros (volumen, área, vértices, validación...) para las
// reconstrucciones propias del repo — se lee como la hoja de especificaciones
// de un instrumento real, no como más prosa, porque son números medidos de
// esta tomografía exacta, no un rango de libro de texto.
function FichaTecnica({ ficha }) {
  return (
    <div className="rounded-xl border border-accent/25 bg-accent-soft/40 p-4">
      {ficha.titulo ? (
        <h3 className="mb-3 text-[0.68rem] font-bold uppercase tracking-wider text-accent-strong">
          {ficha.titulo}
        </h3>
      ) : null}
      <dl className="grid grid-cols-2 gap-x-3 gap-y-2.5">
        {ficha.items.map((item) => (
          <div key={item.etiqueta}>
            <dt className="text-[0.62rem] uppercase tracking-wide text-ink-faint">{item.etiqueta}</dt>
            <dd className="font-display text-sm font-semibold text-ink">{item.valor}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

// Su propio apartado, con nombre y borde propios — no son solo párrafos
// sueltos debajo del título de la estructura, son el "Cuadro de
// Conocimiento": previo / nuevo / aplicación clínica, como bloque.
function CuadroDeConocimiento({ structure }) {
  return (
    <div className="rounded-xl border border-border bg-surface-raised/60 p-4 shadow-glass">
      <h3 className="mb-3 flex items-center gap-2 text-[0.68rem] font-bold uppercase tracking-wider text-ink-faint">
        <span className="h-px flex-1 bg-gradient-to-r from-accent/60 to-transparent" aria-hidden="true" />
        Cuadro de Conocimiento
        <span className="h-px flex-1 bg-gradient-to-l from-accent/60 to-transparent" aria-hidden="true" />
      </h3>
      <div className="space-y-5">
        <Seccion titulo="Lo que sabía previamente">
          <ParrafoSimple texto={structure.conocimientoPrevio} />
        </Seccion>

        <Seccion titulo="Lo que sé después de estudiar">
          <Subsecciones items={structure.conocimientoNuevo} />
        </Seccion>

        <Seccion titulo="Aplicación clínica">
          <CasoClinico caso={structure.aplicacionClinica} />
        </Seccion>
      </div>
    </div>
  );
}

function Seccion({ titulo, children }) {
  return (
    <div>
      <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-accent-strong">
        {titulo}
      </h4>
      {children}
    </div>
  );
}

function ParrafoSimple({ texto }) {
  if (!texto) {
    return <p className="text-sm italic leading-relaxed text-ink-faint">Pendiente de completar.</p>;
  }
  return <p className="text-sm leading-relaxed text-ink-dim">{texto}</p>;
}

// El apartado "nuevo" viene como una lista de subtemas (p. ej. "Ubicación y
// morfología", "Capas de la pared"...) — cada uno con su propio encabezado,
// tal como está estructurado el Cuadro de Conocimiento original, en vez de
// aplastarlos en un solo párrafo corrido.
function Subsecciones({ items }) {
  if (!items || items.length === 0) {
    return <p className="text-sm italic leading-relaxed text-ink-faint">Pendiente de completar.</p>;
  }
  return (
    <div className="space-y-3">
      {items.map((item, i) => (
        <p key={i} className="text-sm leading-relaxed text-ink-dim">
          {item.titulo ? <span className="font-semibold text-ink">{item.titulo}: </span> : null}
          {item.texto}
        </p>
      ))}
    </div>
  );
}

// La aplicación clínica es un caso con nombre propio (p. ej. "Insuficiencia
// cardiaca") seguido de su explicación — el título merece distinguirse del
// cuerpo, no quedar fundido con la primera oración.
function CasoClinico({ caso }) {
  if (!caso || (!caso.titulo && !caso.texto)) {
    return <p className="text-sm italic leading-relaxed text-ink-faint">Pendiente de completar.</p>;
  }
  return (
    <div className="rounded-md border border-warn/25 bg-warn/5 p-3">
      {caso.titulo ? (
        <p className="mb-1 text-sm font-semibold text-ink">{caso.titulo}</p>
      ) : null}
      <p className="text-sm leading-relaxed text-ink-dim">{caso.texto}</p>
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
          <motion.button
            key={rel.id}
            type="button"
            onClick={() => onSelectRelated(rel.id)}
            title={rel.sinMalla ? "Esta estructura aún no tiene malla 3D propia" : undefined}
            whileHover={{ scale: 1.05, y: -1 }}
            whileTap={{ scale: 0.97 }}
            className={`rounded-full border px-2.5 py-1 text-xs font-medium transition-colors ${
              rel.sinMalla
                ? "border-dashed border-border text-ink-faint hover:bg-surface-raised"
                : "border-accent/30 bg-accent-soft text-accent-ink shadow-glow-accent-sm hover:bg-accent/25"
            }`}
          >
            {rel.nombre}
          </motion.button>
        ))}
      </div>
    </div>
  );
}
