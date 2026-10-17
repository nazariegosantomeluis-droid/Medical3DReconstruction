import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import ImagePlaceholder from "./ImagePlaceholder";
import Lightbox from "./Lightbox";

const fadeVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: 0.18 } },
};

export default function InfoPanel({ structure, meshName, allStructures, onClose, onSelectRelated }) {
  const nombre = structure?.nombre ?? meshName;
  const [lightboxOpen, setLightboxOpen] = useState(false);

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
          variants={fadeVariants}
          initial="hidden"
          animate="show"
          className="space-y-3.5 p-6"
        >
          {structure.imagenUrl ? (
            <>
              <button
                type="button"
                onClick={() => setLightboxOpen(true)}
                aria-label="Ver imagen completa"
                className="block h-40 w-full cursor-zoom-in overflow-hidden rounded-lg border border-border"
              >
                <img src={structure.imagenUrl} alt={nombre} className="h-full w-full object-cover" />
              </button>
              <Lightbox
                src={lightboxOpen ? structure.imagenUrl : null}
                alt={nombre}
                onClose={() => setLightboxOpen(false)}
              />
            </>
          ) : structure.sinMalla ? (
            <ImagePlaceholder structureId={structure.id} />
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

          <CuadroConocimiento key={structure.id} structure={structure} />

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
    <h3 className="flex items-center gap-2 pt-1 text-[0.68rem] font-bold uppercase tracking-wider text-ink-faint">
      <span className="h-px flex-1 bg-gradient-to-r from-accent/60 to-transparent" aria-hidden="true" />
      {texto}
      <span className="h-px flex-1 bg-gradient-to-l from-accent/60 to-transparent" aria-hidden="true" />
    </h3>
  );
}

// El Cuadro de Conocimiento ya no se revela todo de una — cada estructura
// trae varios temas (lo que ya se sabía, cada subtema nuevo, la aplicación
// clínica), y mostrarlos todos a la vez como una pared de texto no ayuda a
// estudiar. En cambio, cada tema es un botón: se arranca mostrando el
// primero, y hacer clic en otro botón reemplaza el contenido de abajo —
// el estudio avanza "de a poco", un tema a la vez, a ritmo de quien lee.
function CuadroConocimiento({ structure }) {
  const secciones = useMemo(() => buildSecciones(structure), [structure]);
  // Arranca sin ningún tema elegido a propósito: la información aparece
  // recién cuando se hace clic en un tema de la lista, de a uno — no hay
  // una primera burbuja ya puesta ahí esperando. Es lo que hace que el
  // estudio avance "poco a poco" en vez de encontrarse todo servido.
  const [activeId, setActiveId] = useState(null);

  if (secciones.length === 0) return null;

  const activa = secciones.find((s) => s.id === activeId) ?? null;

  return (
    <div className="space-y-3">
      <SeccionTitulo texto="Cuadro de Conocimiento" />

      <div
        role="tablist"
        aria-label="Temas de este cuadro de conocimiento"
        className="max-h-48 space-y-0.5 overflow-y-auto rounded-xl border border-border bg-surface-raised/40 p-1.5"
      >
        {secciones.map((sec) => {
          const active = sec.id === activa?.id;
          return (
            <button
              key={sec.id}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setActiveId(active ? null : sec.id)}
              className={`flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-[0.8rem] leading-snug transition-colors ${
                active
                  ? "bg-accent-soft text-accent-ink"
                  : "text-ink-dim hover:bg-surface-raised hover:text-ink"
              }`}
            >
              <span
                className={`h-1.5 w-1.5 shrink-0 rounded-full ${active ? "bg-accent-strong shadow-glow-accent-sm" : "bg-border"}`}
                aria-hidden="true"
              />
              <span className="min-w-0 flex-1 truncate">{sec.titulo}</span>
            </button>
          );
        })}
      </div>

      <AnimatePresence mode="wait">
        {activa ? (
          <motion.div
            key={activa.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.16 }}
          >
            <Bubble tone={activa.tone} icon={activa.icon}>
              <EtiquetaBurbuja>{activa.titulo}</EtiquetaBurbuja>
              {activa.render()}
            </Bubble>
          </motion.div>
        ) : (
          <motion.p
            key="placeholder"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="rounded-xl border border-dashed border-border px-3.5 py-5 text-center text-xs leading-relaxed text-ink-faint"
          >
            Elegí un tema de la lista para ver su contenido.
          </motion.p>
        )}
      </AnimatePresence>
    </div>
  );
}

// Arma la lista de temas/botones a partir de los mismos campos que ya
// traía cada estructura (conocimientoPrevio / conocimientoNuevo /
// aplicacionClinica) — es el único esquema de datos ahora, tanto para las
// ~33 estructuras originales como para los temas que venían de la guía de
// alto rendimiento (ya no existen como categoría aparte: son subtemas más
// dentro del Cuadro de Conocimiento de su sistema).
function buildSecciones(structure) {
  const secciones = [];

  if (structure.conocimientoPrevio) {
    secciones.push({
      id: "previo",
      titulo: "Lo que ya sabía",
      tone: "previo",
      icon: <IconoPrevio />,
      render: () => <ParrafoSimple texto={structure.conocimientoPrevio} />,
    });
  }

  const multiple = (structure.conocimientoNuevo ?? []).length > 1;
  (structure.conocimientoNuevo ?? []).forEach((item, i) => {
    // item.bloques (contenido que viene de la guía de alto rendimiento,
    // fusionado en un solo tema con varios párrafos/tablas en su orden
    // original) o el par texto/tablas de siempre (estructuras originales)
    // — un tema, un botón, cualquiera sea su forma.
    const bloques = item.bloques ?? [{ texto: item.texto, tablas: item.tablas }];
    secciones.push({
      id: `nuevo-${i}`,
      titulo: item.titulo || (multiple ? shortLabel(bloques[0]) : "Lo que sé después de estudiar"),
      tone: "nuevo",
      icon: <IconoNuevo />,
      render: () => (
        <>
          {bloques.map((bloque, j) => <Bloque key={j} bloque={bloque} />)}
        </>
      ),
    });
  });

  if (structure.aplicacionClinica?.titulo || structure.aplicacionClinica?.texto) {
    secciones.push({
      id: "aplicacion",
      titulo: "Aplicación clínica",
      tone: "aplicacion",
      icon: <IconoAplicacion />,
      render: () => <CasoClinico caso={structure.aplicacionClinica} />,
    });
  }

  return secciones;
}

// Para los temas que no traen un título propio (sobre todo contenido que
// venía de la guía de alto rendimiento, donde cada párrafo u tabla del
// documento original es un ítem sin encabezado) el botón necesita algo
// más útil que "Tema 3" para que elegir entre varios tenga sentido de un
// vistazo.
function shortLabel(bloque) {
  const texto = (bloque.texto || "").trim();
  // Un texto que es solo una cita entre paréntesis (p. ej. "(Guyton, cap.
  // 12...)") no sirve como vista previa del tema: la tabla o el resto del
  // contenido dicen mucho más de qué trata.
  const esSoloCita = /^\(.*\)$/s.test(texto);
  if (texto && !esSoloCita) {
    const primeraOracion = texto.split(/(?<=[.:;])\s/)[0];
    return primeraOracion.length <= 42 ? primeraOracion : `${texto.slice(0, 38).trimEnd()}…`;
  }
  const primeraTabla = bloque.tablas?.[0];
  if (primeraTabla?.headers?.length) {
    return primeraTabla.headers.slice(0, 2).join(" / ");
  }
  if (texto) {
    return texto.length <= 42 ? texto : `${texto.slice(0, 38).trimEnd()}…`;
  }
  return "Tabla";
}

// Un bloque es un párrafo y/o una o más tablas, en el orden en que
// aparecían en el documento original — varios bloques seguidos arman un
// tema completo sin aplastar la cita bibliográfica contra el texto
// principal ni el texto contra la tabla que describe.
function Bloque({ bloque }) {
  const texto = (bloque.texto || "").trim();
  const esSoloCita = /^\(.*\)$/s.test(texto);
  return (
    <div className="space-y-2">
      {texto && !esSoloCita ? <p className="text-sm leading-relaxed text-ink-dim">{texto}</p> : null}
      {bloque.tablas?.map((t, j) => <Tabla key={j} tabla={t} />)}
      {esSoloCita ? <p className="text-xs italic text-ink-faint">{texto}</p> : null}
    </div>
  );
}

// Burbuja individual: ícono redondo + contenido, con el tono de color que
// le corresponda (previo = neutro, nuevo = base, aplicación = alerta
// clínica).
function Bubble({ tone = "nuevo", icon, children }) {
  const toneClasses = {
    previo: "border-border bg-surface-raised/50",
    nuevo: "border-border bg-surface-raised/80 shadow-glass",
    aplicacion: "border-warn/30 bg-warn/5",
  };
  const iconToneClasses = {
    previo: "bg-surface text-ink-faint",
    nuevo: "bg-accent-soft text-accent-strong",
    aplicacion: "bg-warn/15 text-warn",
  };
  return (
    <div className={`flex gap-3 rounded-xl border p-3.5 ${toneClasses[tone]}`}>
      <span
        className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${iconToneClasses[tone]}`}
        aria-hidden="true"
      >
        {icon}
      </span>
      <div className="min-w-0 flex-1 space-y-1.5">{children}</div>
    </div>
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

// Soporte de tablas reales dentro de una burbuja — buena parte del
// contenido que viene de la guía de alto rendimiento vive en tablas
// (valores normales, criterios de ECG, fórmulas), no en párrafos.
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
