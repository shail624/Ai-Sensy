export interface SettingsSection {
  key: string;
  label: string;
  path: string;
  /** The permission the API enforces for this section's reads. */
  permission: string;
  description: string;
}

/**
 * The settings areas, each gated by the permission its own endpoints enforce.
 *
 * Preferences is deliberately gated on `auth:self` rather than `settings:read`: it is the user's
 * own record, every account holds that permission, and someone with no administrative access
 * should still reach their own preferences.
 */
export const SETTINGS_SECTIONS: SettingsSection[] = [
  {
    key: "organization",
    label: "Organization",
    path: "/settings/organization",
    permission: "settings:read",
    description: "Who this platform runs for — name, timezone and default locale.",
  },
  {
    key: "application",
    label: "Application",
    path: "/settings/application",
    permission: "settings:read",
    description: "The configuration store, by scope, and what the platform holds in it.",
  },
  {
    key: "flags",
    label: "Feature flags",
    path: "/settings/flags",
    permission: "settings:read",
    description: "Flags registered on this deployment and whether they are switched on.",
  },
  {
    key: "preferences",
    label: "My preferences",
    path: "/settings/preferences",
    permission: "auth:self",
    description: "Your own settings, stored against your account.",
  },
];

/** Any one of these is enough to reach the settings area at all. */
export const SETTINGS_PERMISSIONS: string[] = [
  ...new Set(SETTINGS_SECTIONS.map((section) => section.permission)),
];
