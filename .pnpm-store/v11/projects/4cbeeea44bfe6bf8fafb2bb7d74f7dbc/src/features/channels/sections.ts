export interface ChannelSection {
  key: string;
  label: string;
  path: string;
  description: string;
}

/**
 * The two halves of channel management, kept as data so the sub-navigation and the page header read
 * one list.
 *
 * Both sit behind the same permission (`waba:read` to see, `waba:manage` to change), because a
 * number belongs to an account — there is no meaningful access to one without the other.
 */
export const CHANNEL_SECTIONS: ChannelSection[] = [
  {
    key: "accounts",
    label: "Business accounts",
    path: "/channels/accounts",
    description: "Connected WhatsApp Business Accounts and the credentials they send with.",
  },
  {
    key: "numbers",
    label: "Phone numbers",
    path: "/channels/numbers",
    description: "The numbers those accounts own, with their quality and sending limits.",
  },
];
