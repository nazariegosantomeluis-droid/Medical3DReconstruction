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
        display: ["Space Grotesk", "Inter", "ui-sans-serif", "sans-serif"],
      },
      boxShadow: {
        "glow-accent": "0 0 50px -12px rgba(192,82,91,0.5)",
        "glow-accent-sm": "0 0 20px -6px rgba(192,82,91,0.55)",
        glass: "0 8px 32px -8px rgba(0,0,0,0.45)",
      },
      keyframes: {
        "pulse-slow": {
          "0%, 100%": { opacity: 0.55, transform: "scale(1)" },
          "50%": { opacity: 0.9, transform: "scale(1.06)" },
        },
        drift: {
          "0%, 100%": { transform: "translate(0, 0)" },
          "50%": { transform: "translate(3%, -4%)" },
        },
        "fade-in-up": {
          "0%": { opacity: 0, transform: "translateY(6px)" },
          "100%": { opacity: 1, transform: "translateY(0)" },
        },
      },
      animation: {
        "pulse-slow": "pulse-slow 5s ease-in-out infinite",
        drift: "drift 16s ease-in-out infinite",
        "drift-slow": "drift 24s ease-in-out infinite reverse",
        "fade-in-up": "fade-in-up 0.4s ease-out both",
      },
    },
  },
  plugins: [],
};
