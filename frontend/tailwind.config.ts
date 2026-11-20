import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        crypt: "#0b0a10",
        "crypt-2": "#14121c",
        "crypt-3": "#1d1a28",
        stone: { DEFAULT: "#2a2735", light: "#3b3748", dark: "#1a1822" },
        bone: { DEFAULT: "#ece6d9", dim: "#b9b2a4", faint: "#8a8374" },
        ecto: { DEFAULT: "#7cf5a5", dim: "#4fb87a", glow: "rgba(124,245,165,0.35)" },
        blood: { DEFAULT: "#e5484d", dim: "#a8343a" },
        candle: { DEFAULT: "#ffcf70", deep: "#ff9a3c" },
        paper: { DEFAULT: "#efe3c8", edge: "#cdb98f", ink: "#2b2118", faded: "#6b5a43" },
      },
      fontFamily: {
        display: ["var(--font-display)", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
        hand: ["var(--font-hand)", "serif"],
      },
      boxShadow: {
        ecto: "0 0 24px rgba(124,245,165,0.45), 0 0 64px rgba(124,245,165,0.15)",
        candle: "0 0 18px rgba(255,207,112,0.6)",
        paper: "0 30px 60px -20px rgba(0,0,0,0.8), inset 0 0 80px rgba(107,90,67,0.35)",
      },
      keyframes: {
        flicker: {
          "0%, 100%": { opacity: "1", transform: "scaleY(1) translateY(0)" },
          "25%": { opacity: "0.85", transform: "scaleY(1.06) translateY(-1px)" },
          "50%": { opacity: "0.95", transform: "scaleY(0.96) translateY(0)" },
          "75%": { opacity: "0.8", transform: "scaleY(1.03) translateY(-0.5px)" },
        },
        "pulse-glow": {
          "0%, 100%": { boxShadow: "0 0 16px rgba(124,245,165,0.25)" },
          "50%": { boxShadow: "0 0 36px rgba(124,245,165,0.55)" },
        },
      },
      animation: {
        flicker: "flicker 1.6s ease-in-out infinite",
        "pulse-glow": "pulse-glow 3s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
