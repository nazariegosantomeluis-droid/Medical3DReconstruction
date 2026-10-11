import { useState } from "react";
import { motion } from "framer-motion";
import ImagePlaceholder from "./ImagePlaceholder";

// El "Cuadro de Conocimiento" se revela como una secuencia de mensajes que
// van apareciendo uno tras otro (staggerChildren), no como un bloque de
// texto que aparece de golpe — es lo que le da el aire de conversación/
// chat que se pidió, sin inventar una interfaz de chat de verdad (no hay
// nadie del otro lado respondiendo), solo el RITMO de revelado.
const bubbleContainerVariants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.09, delayChildren: 0.06 } },
};

const bubbleVariants = {
  hidden: { opacity: 0, y: 12, scale: 0.98 },
  show: { opacity: 1, y: 0, scale: 1, transition: { type: "spring", stiffness: 380, damping: 30 } },
};

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
          variants={bubbleContainerVariants}
          initial="hidden"
          animate="show"
          className="space-y-3.5 p-6"
        >
          {structure.imagenUrl ? (
            <motion.img
              variants={bubbleVariants}
              src={structure.imagenUrl}
              alt={nombre}
              className="h-40 w-full rounded-lg border border-border object-cover"
            />
          ) : structure.sinMalla ? (
            <motion.div variants={bubbleVariants}>
              <ImagePlaceholder structureId={structure.id} />
            </motion.div>
          ) : null}

          {structure.notaSinMalla ? (
            <motion.p
              variants={bubbleVariants}
              className="rounded-md border border-warn/30 bg-warn/10 px-3 py-2 text-xs text-warn"
            >
              {structure.notaSinMalla}
            </motion.p>
          ) : null}

          {structure.notaEspecimen ? (
            <motion.p
              variants={bubbleVariants}
              className="rounded-md border border-accent/30 bg-accent-soft px-3 py-2 text-xs text-accent-ink"
            >
              {structure.notaEspecimen}
            </motion.p>
          ) : null}

          {structure.fichaTecnica ? (
            <motion.div variants={bubbleVariants}>
              <FichaTecnica ficha={structure.fichaTecnica} />
            </motion.div>
          ) : null}

          {structure.tipo === "guia" ? (
            <GuiaContenido structure={structure} />
          ) : (
            <>
              <SeccionTitulo texto="Cuadro de Conocimiento" />

              <Bubble tone="previo" icon={<IconoPrevio />}>
                <EtiquetaBurbuja>Lo que sabía previamente</EtiquetaBurbuja>
                <ParrafoSimple texto={structure.conocimientoPrevio} />
              </Bubble>

              <SubseccionesBurbujas items={structure.conocimientoNuevo} />

              <Bubble tone="aplicacion" icon={<IconoAplicacion />}>
                <EtiquetaBurbuja>Aplicación clínica</EtiquetaBurbuja>
                <CasoClinico caso={structure.aplicacionClinica} />
              </Bubble>
            </>
          )}

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

function SeccionTitulo({ texto }) {
  return (
    <motion.h3
      variants={bubbleVariants}
      className="flex items-center gap-2 pt-1 text-[0.68rem] font-bold uppercase tracking-wider text-ink-faint"
    >
      <span className="h-px flex-1 bg-gradient-to-r from-accent/60 to-transparent" aria-hidden="true" />
      {texto}
      <span className="h-px flex-1 bg-gradient-to-l from-accent/60 to-transparent" aria-hidden="true" />
    </motion.h3>
  );
}

// Las entradas de la Guía de Alto Rendimiento no son una estructura
// anatómica con "lo que sabía antes / después" — son material de consulta
// directa (valores normales, criterios de ECG, fórmulas), así que en vez
// de forzar ese molde se muestran directo: cada elemento (texto o tabla,
// en el orden original del documento) es su propia burbuja, con la regla
// mnemotécnica ("clave") destacada aparte si la hay, y las preguntas de
// práctica como tarjetas con la respuesta oculta hasta hacer clic.
function GuiaContenido({ structure }) {
  return (
    <>
      <SeccionTitulo texto="Guía de alto rendimiento" />

      {structure.clave ? (
        <Bubble tone="clave" icon={<IconoClave />}>
          <EtiquetaBurbuja>Para recordar</EtiquetaBurbuja>
          <p className="text-sm leading-relaxed text-ink-dim">{structure.clave}</p>
        </Bubble>
      ) : null}

      {(structure.conocimientoNuevo ?? []).map((item, i) => (
        <Bubble key={i} tone="nuevo" icon={<IconoNuevo />}>
          {item.texto ? <p className="text-sm leading-relaxed text-ink-dim">{item.texto}</p> : null}
          {item.tablas?.map((t, j) => <Tabla key={j} tabla={t} />)}
        </Bubble>
      ))}

      {structure.preguntas?.length ? (
        <div className="space-y-2.5 pt-1">
          <EtiquetaBurbuja>{structure.preguntasIntro ?? "Preguntas de práctica"}</EtiquetaBurbuja>
          {structure.preguntas.map((p) => (
            <PreguntaCard key={p.numero} pregunta={p} />
          ))}
        </div>
      ) : null}
    </>
  );
}

// Tarjeta de pregunta de opción múltiple con la respuesta oculta hasta
// que se hace clic — invita a responder antes de leer la explicación, en
// vez de que la respuesta aparezca ya resuelta junto con el enunciado.
function PreguntaCard({ pregunta }) {
  const [revealed, setRevealed] = useState(false);
  return (
    <motion.div variants={bubbleVariants} className="rounded-xl border border-border bg-surface-raised/80 p-3.5 shadow-glass">
      <p className="text-sm leading-relaxed text-ink">
        <span className="font-semibold text-accent-strong">{pregunta.numero}. </span>
        {pregunta.enunciado}
      </p>
      <ul className="mt-2 space-y-1">
        {Object.entries(pregunta.opciones).map(([letra, texto]) => {
          const esCorrecta = revealed && letra === pregunta.respuestaLetra;
          return (
            <li
              key={letra}
              className={`rounded-md px-2 py-1 text-sm transition-colors ${
                esCorrecta ? "bg-ok/15 text-ok" : "text-ink-dim"
              }`}
            >
              <span className="font-medium">{letra}) </span>
              {texto}
            </li>
          );
        })}
      </ul>
      {revealed ? (
        <motion.p
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          className="mt-2 rounded-md border border-ok/25 bg-ok/5 px-2.5 py-2 text-xs leading-relaxed text-ink-dim"
        >
          <span className="font-semibold text-ok">Respuesta {pregunta.respuestaLetra}): </span>
          {pregunta.respuestaTexto}
        </motion.p>
      ) : (
        <button
          type="button"
          onClick={() => setRevealed(true)}
          className="mt-2 rounded-full border border-accent/30 bg-accent-soft px-3 py-1 text-xs font-medium text-accent-ink transition-colors hover:bg-accent/25"
        >
          Mostrar respuesta
        </button>
      )}
    </motion.div>
  );
}

function IconoClave() {
  return (
    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <circle cx="8" cy="15" r="4" />
      <path d="M11 12l8-8M16 7l2 2M19 4l2 2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// Burbuja individual: ícono redondo + contenido, con el tono de color que
// le corresponda (previo = neutro, nuevo = base, aplicación = alerta
// clínica) — el mismo lenguaje visual que un mensaje de chat, sin fingir
// que hay alguien del otro lado.
function Bubble({ tone = "nuevo", icon, children }) {
  const toneClasses = {
    previo: "border-border bg-surface-raised/50",
    nuevo: "border-border bg-surface-raised/80 shadow-glass",
    aplicacion: "border-warn/30 bg-warn/5",
    clave: "border-ok/30 bg-ok/5",
  };
  const iconToneClasses = {
    previo: "bg-surface text-ink-faint",
    nuevo: "bg-accent-soft text-accent-strong",
    aplicacion: "bg-warn/15 text-warn",
    clave: "bg-ok/15 text-ok",
  };
  return (
    <motion.div
      variants={bubbleVariants}
      className={`flex gap-3 rounded-xl border p-3.5 ${toneClasses[tone]}`}
    >
      <span
        className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${iconToneClasses[tone]}`}
        aria-hidden="true"
      >
        {icon}
      </span>
      <div className="min-w-0 flex-1 space-y-1.5">{children}</div>
    </motion.div>
  );
}

function EtiquetaBurbuja({ children }) {
  return <p className="text-[0.66rem] font-semibold uppercase tracking-wide text-ink-faint">{children}</p>;
}

function IconoPrevio() {
  return (
    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <path d="M12 3a6 6 0 0 0-3.5 10.9c.6.44.9.8.9 1.6v.5h5.2v-.5c0-.8.3-1.16.9-1.6A6 6 0 0 0 12 3Z" strokeLinejoin="round" />
      <path d="M9.5 19h5M10.2 21h3.6" strokeLinecap="round" />
    </svg>
  );
}

function IconoNuevo() {
  return (
    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" strokeLinecap="round" />
      <circle cx="12" cy="12" r="2.6" />
    </svg>
  );
}

function IconoAplicacion() {
  return (
    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <path d="M8 3v3M16 3v3" strokeLinecap="round" />
      <path d="M5 6h14v13a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6Z" strokeLinejoin="round" />
      <path d="M9 13l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ParrafoSimple({ texto }) {
  if (!texto) {
    return <p className="text-sm italic leading-relaxed text-ink-faint">Pendiente de completar.</p>;
  }
  return <p className="text-sm leading-relaxed text-ink-dim">{texto}</p>;
}

// Cada subtema de "lo que sé después de estudiar" es SU PROPIA burbuja (no
// un párrafo más dentro de una burbuja grande) — así el stagger de entrada
// hace que se revelen uno por uno, como una explicación que va llegando en
// partes en vez de un bloque de texto que aparece todo junto.
function SubseccionesBurbujas({ items }) {
  if (!items || items.length === 0) {
    return (
      <Bubble tone="nuevo" icon={<IconoNuevo />}>
        <EtiquetaBurbuja>Lo que sé después de estudiar</EtiquetaBurbuja>
        <p className="text-sm italic leading-relaxed text-ink-faint">Pendiente de completar.</p>
      </Bubble>
    );
  }
  return (
    <>
      {items.map((item, i) => (
        <Bubble key={i} tone="nuevo" icon={<IconoNuevo />}>
          {i === 0 ? <EtiquetaBurbuja>Lo que sé después de estudiar</EtiquetaBurbuja> : null}
          <p className="text-sm leading-relaxed text-ink-dim">
            {item.titulo ? <span className="font-semibold text-ink">{item.titulo}: </span> : null}
            {item.texto}
          </p>
          {item.tablas?.map((t, j) => <Tabla key={j} tabla={t} />)}
        </Bubble>
      ))}
    </>
  );
}

// Soporte de tablas reales dentro de una burbuja — la guía de alto
// rendimiento vive sobre todo en tablas (valores normales, criterios de
// ECG, fórmulas), no en párrafos, así que el Cuadro de Conocimiento
// necesita poder mostrar una tabla de verdad, no aplastarla en texto.
function Tabla({ tabla }) {
  return (
    <div className="mt-2 overflow-x-auto rounded-lg border border-border/70">
      <table className="w-full min-w-max border-collapse text-xs">
        <thead>
          <tr className="bg-surface">
            {tabla.headers.map((h, i) => (
              <th key={i} className="whitespace-nowrap border-b border-border px-2.5 py-1.5 text-left font-semibold text-ink">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {tabla.rows.map((row, i) => (
            <tr key={i} className={i % 2 === 1 ? "bg-surface/60" : ""}>
              {row.map((cell, j) => (
                <td key={j} className="border-b border-border/40 px-2.5 py-1.5 align-top text-ink-dim">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
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
    <>
      {caso.titulo ? <p className="text-sm font-semibold text-ink">{caso.titulo}</p> : null}
      <p className="text-sm leading-relaxed text-ink-dim">{caso.texto}</p>
    </>
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
    <motion.div variants={bubbleVariants} className="border-t border-border pt-5">
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
    </motion.div>
  );
}
