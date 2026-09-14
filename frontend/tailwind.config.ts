import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "monospace"],
      },
      colors: {
        ink: "#0f1419",
        panel: "#161d27",
        line: "#2a3544",
        gold: "#c4a35a",
        paper: "#e8edf2",
      },
    },
  },
  plugins: [],
};

export default config;
