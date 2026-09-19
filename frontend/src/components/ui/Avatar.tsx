interface AvatarProps {
  name: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const SIZES = {
  sm: "h-8 w-8 text-xs",
  md: "h-10 w-10 text-sm",
  lg: "h-12 w-12 text-base",
} as const;

// A small, stable palette — the same name always lands on the same colour, so a contact keeps its
// identity across screens.
//
// Every tone is the darkest-but-one step of the hue it started from, chosen so the white initials
// on it clear 4.5:1. The previous set was described as "tuned for legible white text" and measured
// between 2.15:1 and 4.47:1 — nine of the ten failed, the amber worst of all. Hue is preserved, so
// a contact whose avatar was blue is still blue.
const COLORS = [
  "#6164f1", "#0b7caf", "#0c855d", "#a36907", "#e91414",
  "#8452f5", "#e0177a", "#0e8376", "#c35305", "#1b6ef5",
];

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  const first = parts[0]?.[0] ?? "";
  const last = parts.length > 1 ? (parts[parts.length - 1]?.[0] ?? "") : "";
  return (`${first}${last}` || "?").toUpperCase();
}

function colorFor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i += 1) hash = (hash * 31 + name.charCodeAt(i)) | 0;
  return COLORS[Math.abs(hash) % COLORS.length] ?? COLORS[0]!;
}

/** Deterministic initials avatar — no image dependency, consistent colour per name. */
export function Avatar({ name, size = "md", className = "" }: AvatarProps): JSX.Element {
  return (
    <span
      aria-hidden
      className={`inline-flex shrink-0 items-center justify-center rounded-full font-semibold text-white ${SIZES[size]} ${className}`}
      style={{ backgroundColor: colorFor(name || "?") }}
    >
      {initials(name)}
    </span>
  );
}
