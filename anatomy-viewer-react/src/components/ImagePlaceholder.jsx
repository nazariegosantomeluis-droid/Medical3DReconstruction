import { useEffect, useRef, useState } from "react";
import Lightbox from "./Lightbox";

const STORAGE_PREFIX = "anatomy-viewer:pasted-image:";

// Persistencia 100% local (localStorage de este navegador): el sitio es
// estático (GitHub Pages/Vercel, sin backend), así que "pegar una imagen"
// no puede subirla a ningún lado — queda guardada en ESTE dispositivo,
// para quien la pegó. Es justo lo que pidieron: un lugar para pegar
// imágenes propias en las estructuras que no tienen malla 3D, sin montar
// un backend para un visor que hasta ahora era enteramente estático.
function readStoredImage(structureId) {
  try {
    return localStorage.getItem(STORAGE_PREFIX + structureId);
  } catch {
    return null;
  }
}

function writeStoredImage(structureId, dataUrl) {
  try {
    if (dataUrl) {
      localStorage.setItem(STORAGE_PREFIX + structureId, dataUrl);
    } else {
      localStorage.removeItem(STORAGE_PREFIX + structureId);
    }
  } catch {
    // localStorage lleno o bloqueado (modo privado) — la imagen igual se
    // ve durante esta sesión, solo no sobrevive a un refresh. No es motivo
    // para romper la interfaz.
  }
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// Recuadro para estructuras sin malla 3D propia (conceptos, temas de
// fisiología, microanatomía): un lugar explícito para pegar (Ctrl+V) o
// subir una imagen de referencia propia, ya que el modelo 3D no puede
// mostrar nada ahí. Guarda en localStorage, por dispositivo.
export default function ImagePlaceholder({ structureId }) {
  const [imageSrc, setImageSrc] = useState(() => readStoredImage(structureId));
  const [isDragOver, setIsDragOver] = useState(false);
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const fileInputRef = useRef(null);
  const boxRef = useRef(null);

  useEffect(() => {
    setImageSrc(readStoredImage(structureId));
  }, [structureId]);

  const applyFile = async (file) => {
    if (!file || !file.type.startsWith("image/")) return;
    const dataUrl = await fileToDataUrl(file);
    setImageSrc(dataUrl);
    writeStoredImage(structureId, dataUrl);
  };

  const handlePaste = async (event) => {
    const item = Array.from(event.clipboardData?.items ?? []).find((it) => it.type.startsWith("image/"));
    if (!item) return;
    event.preventDefault();
    await applyFile(item.getAsFile());
  };

  const handleDrop = async (event) => {
    event.preventDefault();
    setIsDragOver(false);
    await applyFile(event.dataTransfer.files?.[0]);
  };

  const handleFileInput = async (event) => {
    await applyFile(event.target.files?.[0]);
    event.target.value = "";
  };

  const handleRemove = (event) => {
    event.stopPropagation();
    setImageSrc(null);
    writeStoredImage(structureId, null);
  };

  if (imageSrc) {
    return (
      <>
        <div className="group relative overflow-hidden rounded-lg border border-border">
          <button
            type="button"
            onClick={() => setLightboxOpen(true)}
            aria-label="Ver imagen completa"
            className="block h-40 w-full cursor-zoom-in"
          >
            <img src={imageSrc} alt="" className="h-full w-full object-cover" />
          </button>
          <button
            type="button"
            onClick={handleRemove}
            aria-label="Quitar imagen pegada"
            className="absolute right-2 top-2 rounded-full bg-black/60 p-1.5 text-white opacity-0 transition-opacity hover:bg-black/80 group-hover:opacity-100"
          >
            <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden="true">
              <path strokeLinecap="round" d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
          <span className="pointer-events-none absolute bottom-2 left-2 rounded-full bg-black/60 px-2 py-0.5 text-[0.6rem] text-white/80">
            Guardada en este dispositivo
          </span>
        </div>
        <Lightbox src={lightboxOpen ? imageSrc : null} onClose={() => setLightboxOpen(false)} />
      </>
    );
  }

  return (
    <div
      ref={boxRef}
      role="button"
      tabIndex={0}
      onClick={() => fileInputRef.current?.click()}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
      }}
      onPaste={handlePaste}
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragOver(true);
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={handleDrop}
      className={`flex h-32 cursor-pointer flex-col items-center justify-center gap-1.5 rounded-lg border-2 border-dashed px-4 text-center outline-none transition-colors ${
        isDragOver
          ? "border-accent bg-accent-soft"
          : "border-border text-ink-faint hover:border-accent/50 hover:text-ink-dim focus-visible:border-accent/50"
      }`}
    >
      <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
        <rect x="3" y="4" width="18" height="16" rx="2" />
        <circle cx="9" cy="10" r="1.6" />
        <path d="M3 17l5-5 4 4 3-3 6 6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <p className="text-[0.72rem] leading-snug">
        Pega una imagen aquí (Ctrl+V) o haz clic para subir una
      </p>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileInput}
        className="hidden"
      />
    </div>
  );
}
