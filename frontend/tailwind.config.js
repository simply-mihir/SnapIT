/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{js,jsx}",
    "./components/**/*.{js,jsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto'],
        serif: ['"Instrument Serif"', 'ui-serif', 'Georgia', 'Cambria', 'serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      colors: {
        // Warm, paper-like neutrals for light mode
        cream: {
          50: "#fbfaf7",
          100: "#f5f2eb",
          200: "#ebe6da",
          300: "#d9d2c0",
        },
        // Deep, near-black neutrals with a warm undertone for dark mode
        ink: {
          900: "#0b0b0c",
          800: "#131315",
          700: "#1c1c1f",
          600: "#2a2a2e",
          500: "#3a3a3f",
        },
        // Signature accent — warm amber, used sparingly
        accent: {
          DEFAULT: "#c79a5b",
          soft: "#e0c28f",
          deep: "#9e7a42",
        },
      },
      boxShadow: {
        soft: "0 10px 30px -12px rgba(0, 0, 0, 0.15)",
        glass: "0 1px 0 0 rgba(255,255,255,0.06) inset, 0 20px 60px -20px rgba(0,0,0,0.35)",
        "glass-light": "0 1px 0 0 rgba(255,255,255,0.9) inset, 0 20px 60px -25px rgba(20,20,20,0.18)",
        glow: "0 0 0 6px rgba(199,154,91,0.08)",
      },
      backgroundImage: {
        "grain": "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='140' height='140'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.35 0'/></filter><rect width='100%25' height='100%25' filter='url(%23n)' opacity='0.5'/></svg>\")",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: 0, transform: "translateY(6px)" },
          "100%": { opacity: 1, transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        blob: {
          "0%, 100%": { transform: "translate(0,0) scale(1)" },
          "33%": { transform: "translate(14px,-10px) scale(1.05)" },
          "66%": { transform: "translate(-10px,12px) scale(0.97)" },
        },
      },
      animation: {
        "fade-in": "fadeIn 400ms cubic-bezier(0.22, 1, 0.36, 1) both",
        "shimmer": "shimmer 2.2s linear infinite",
        "blob": "blob 18s ease-in-out infinite",
      },
      letterSpacing: {
        tightest: "-0.045em",
      },
    },
  },
  plugins: [],
};
