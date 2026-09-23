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
          fg: "var(--color-danger-fg)",
        },
        info: {
          DEFAULT: "var(--color-info)",
          soft: "var(--color-info-soft)",
          "on-soft": "var(--color-info-on-soft)",
        },
        // Reserved channel accent — WhatsApp identity marker only (Doc 05 DS-5).
        channel: "#25D366",
      },
      // `text-*` resolves to the on-soft tone, while `bg-*`/`border-*` keep the base.
      //
      // `index.css` already states the reason: "the base tone is tuned for solid marks (dots,
      // bars) and does not reach 4.5:1 as 12px text on its own tint, which DS-10 requires in both
      // themes." That was true of every background, not only the soft tint — `text-success` on
      // plain white measures 3.37:1 — so a status word written with the base tone failed DS-10
      // wherever it appeared, in more than three hundred places.
      //
      // Fixing the utility rather than the call sites makes the accessible tone the default: an
      // author writing `text-danger` gets the readable red without having to remember which of the
      // two exists. The explicit `-soft` and `-on-soft` names stay, so nothing that spells the
      // tone out loses meaning, and fills, borders and marks are untouched.
      textColor: {
        success: {
          DEFAULT: "var(--color-success-on-soft)",
          soft: "var(--color-success-soft)",
          "on-soft": "var(--color-success-on-soft)",
        },
        warning: {
          DEFAULT: "var(--color-warning-on-soft)",
          soft: "var(--color-warning-soft)",
          "on-soft": "var(--color-warning-on-soft)",
        },
        danger: {
          DEFAULT: "var(--color-danger-on-soft)",
          soft: "var(--color-danger-soft)",
          "on-soft": "var(--color-danger-on-soft)",
          fg: "var(--color-danger-fg)",
        },
        info: {
          DEFAULT: "var(--color-info-on-soft)",
          soft: "var(--color-info-soft)",
          "on-soft": "var(--color-info-on-soft)",
        },
      },
      boxShadow: {
        sm: "var(--shadow-sm)",
        DEFAULT: "var(--shadow-sm)",
        md: "var(--shadow-md)",
        lg: "var(--shadow-lg)",
        card: "var(--shadow-card)",
      },
      borderRadius: {
        sm: "6px",
        DEFAULT: "8px",
        lg: "12px",
        xl: "16px",
        // Named enterprise tiers avoid silently changing legacy/navigation radius utilities.
        control: "10px",
        surface: "12px",
        overlay: "16px",
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
