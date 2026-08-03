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
          // Text on the matching soft fill, at DS-10's 4.5:1 in both themes.
          "on-soft": "var(--color-accent-on-soft)",
        },
        success: {
          DEFAULT: "var(--color-success)",
          soft: "var(--color-success-soft)",
          "on-soft": "var(--color-success-on-soft)",
        },
        warning: {
          DEFAULT: "var(--color-warning)",
          soft: "var(--color-warning-soft)",
          "on-soft": "var(--color-warning-on-soft)",
        },
        danger: {
          DEFAULT: "var(--color-danger)",
          soft: "var(--color-danger-soft)",
          "on-soft": "var(--color-danger-on-soft)",
        },
        info: {
          DEFAULT: "var(--color-info)",
          soft: "var(--color-info-soft)",
          "on-soft": "var(--color-info-on-soft)",
        },
        // Reserved channel accent — WhatsApp identity marker only (Doc 05 DS-5).
        channel: "#25D366",
      },
      boxShadow: {
        sm: "var(--shadow-sm)",
        DEFAULT: "var(--shadow-sm)",
        md: "var(--shadow-md)",
        lg: "var(--shadow-lg)",
      },
      // Three intentional radius tiers: controls, surfaces, and large overlays.
      borderRadius: {
        sm: "6px",
        DEFAULT: "8px",
        md: "8px",
        lg: "10px",
        xl: "12px",
        "2xl": "16px",
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
