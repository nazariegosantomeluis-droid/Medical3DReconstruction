import { useState } from "react";

// Punto de entrada al mapa de conexiones que no depende de acertarle a una
// malla en el visor 3D: 5 de las 23 estructuras (corazón como resumen,
// pericardio, nariz, bronquiolos, alveolos) no tienen pieza propia en el
// modelo, así que sin esto serían inalcanzables — solo se llegaría a ellas
// de rebote, como chip relacionado de otra que sí tiene malla.
export default function StructureIndex({ structures, onSelect }) {
  const [open, setOpen] = useState(false);

  const porSistema = structures.reduce((acc, s) => {
    (acc[s.sistema] ??= []).push(s);
    return acc;
  }, {});

  return (
    <div className="pointer-events-auto absolute left-4 top-16 z-10">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
        className="rounded-md border border-slate-600 bg-slate-800/90 px-3 py-1.5 text-xs
                   font-semibold text-slate-200 shadow-lg transition hover:bg-slate-700"
      >
        {open ? "Cerrar índice" : "Ver todas las estructuras"}
      </button>

      {open ? (
        <div className="mt-2 max-h-[70vh] w-64 overflow-y-auto rounded-lg border border-slate-700 bg-slate-900/95 p-3 shadow-2xl">
          {Object.entries(porSistema).map(([sistema, items]) => (
            <div key={sistema} className="mb-3 last:mb-0">
              <p className="mb-1 text-[0.65rem] font-semibold uppercase tracking-wide text-slate-500">
                {sistema === "respiratorio" ? "Sistema respiratorio" : "Sistema cardiovascular"}
              </p>
              <ul className="space-y-0.5">
                {items.map((s) => (
                  <li key={s.id}>
                    <button
                      type="button"
                      onClick={() => {
                        onSelect(s.id);
                        setOpen(false);
                      }}
                      className="flex w-full items-center justify-between rounded px-2 py-1 text-left text-xs text-slate-200 hover:bg-slate-800"
                    >
                      <span>{s.nombre}</span>
                      {s.sinMalla ? (
                        <span className="ml-2 shrink-0 text-[0.6rem] text-slate-500">sin malla</span>
                      ) : null}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
