/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: { extend: {
    colors: {
      brand: { DEFAULT: "#187F6B", dark: "#126353", soft: "#DDEFE8" },
      canvas: { DEFAULT: "#FFFFFF", alt: "#F7F9F8" },
      ink: "#243B36", muted: { DEFAULT: "#71847D", strong: "#55695F" }, line: "#E4EBE7",
      danger: { DEFAULT: "#B42318", soft: "#FEF3F2" },
      warn: { DEFAULT: "#93370D", soft: "#FFF6E0" },
      calm: { DEFAULT: "#3F544D", soft: "#EEF3F0" },
    },
    fontFamily: { sans: ['"IBM Plex Sans Thai"', "system-ui", "sans-serif"] },
    borderRadius: { app: "10px", panel: "16px" },
  } },
  plugins: [],
};
