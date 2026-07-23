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
          strong: "var(--color-accent-strong)",
          soft: "var(--color-accent-soft)",
          fg: "var(--color-accent-fg)",
        },
        success: { DEFAULT: "var(--color-success)", soft: "var(--color-success-soft)" },
        warning: { DEFAULT: "var(--color-warning)", soft: "var(--color-warning-soft)" },
        danger: { DEFAULT: "var(--color-danger)", soft: "var(--color-danger-soft)" },
        info: { DEFAULT: "var(--color-info)", soft: "var(--color-info-soft)" },
        // Reserved channel accent — WhatsApp identity marker only (Doc 05 DS-5).
        channel: "#25D366",
      },
      boxShadow: {
        sm: "var(--shadow-sm)",
        DEFAULT: "var(--shadow-sm)",
        md: "var(--shadow-md)",
        lg: "var(--shadow-lg)",
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
