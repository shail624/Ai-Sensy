import type { Config } from "tailwindcss";

// Tailwind maps to the semantic design tokens defined as CSS variables in
// src/index.css, so light/dark theming (Doc 05 DS-3/DS-5) is a token swap only.
// Dark mode is class/attribute driven (`class`) to support the theme toggle (DS-8).
const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: ["class", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        canvas: "var(--color-bg-canvas)",
        surface: {
          DEFAULT: "var(--color-bg-surface)",
          2: "var(--color-bg-surface-2)",
        },
        hover: "var(--color-bg-hover)",
        border: {
          DEFAULT: "var(--color-border-default)",
          strong: "var(--color-border-strong)",
        },
        text: {
          primary: "var(--color-text-primary)",
          secondary: "var(--color-text-secondary)",
          disabled: "var(--color-text-disabled)",
        },
        accent: {
          DEFAULT: "var(--color-accent)",
          fg: "var(--color-accent-fg)",
        },
        success: "var(--color-success)",
        warning: "var(--color-warning)",
        danger: "var(--color-danger)",
        info: "var(--color-info)",
        // Reserved channel accent — WhatsApp identity marker only (Doc 05 DS-5).
        channel: "#25D366",
      },
      borderRadius: {
        sm: "6px",
        DEFAULT: "8px",
        lg: "12px",
        xl: "16px",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      ringColor: {
        focus: "var(--color-focus-ring)",
      },
    },
  },
  plugins: [],
};

export default config;
