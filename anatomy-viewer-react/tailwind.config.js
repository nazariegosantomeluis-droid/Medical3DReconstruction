/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      // Mismos tokens que el sitio principal (docs/index.html) — misma
      // marca, mismo tema oscuro, para que /anatomy-viewer/ se sienta parte
      // del mismo producto y no una página aparte con otro estilo.
      colors: {
        bg: "#17181a",
        surface: "#1d1f22",
        "surface-raised": "#26282c",
        border: "#35373b",
        ink: "#e8e9eb",
        "ink-dim": "#9a9da2",
        "ink-faint": "#8d8f95",
        accent: "#a5434b",
        "accent-soft": "rgba(165,67,75,0.16)",
        "accent-strong": "#c0525b",
        "accent-ink": "#f3e4e2",
        ok: "#5da868",
        warn: "#c9974a",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        serif: ["ui-serif", "Georgia", "serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
    },
  },
  plugins: [],
};
