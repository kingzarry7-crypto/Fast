import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./hooks/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.5rem",
      },
      boxShadow: {
        "kz-glow": "0 0 30px rgba(34, 211, 238, 0.15)",
        "kz-glow-lg": "0 0 60px rgba(34, 211, 238, 0.2)",
      },
      backgroundImage: {
        "kz-grid":
          "linear-gradient(rgba(34,211,238,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(34,211,238,0.05) 1px, transparent 1px)",
      },
      backgroundSize: {
        "kz-grid": "40px 40px",
      },
    },
  },
  plugins: [],
};

export default config;
