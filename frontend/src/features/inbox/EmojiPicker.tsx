import { useState } from "react";

/** A small built-in emoji set, grouped like WhatsApp's picker (no download, works offline). */
export const EMOJI_GROUPS: { name: string; icon: string; emoji: string[] }[] = [
  {
    name: "Smileys",
    icon: "😀",
    emoji: ["😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣", "😊", "😇", "🙂", "😉", "😍", "🥰", "😘", "😋", "😎", "🤩", "🥳", "🤗", "🤔", "🤨", "😐", "😶", "🙄", "😏", "😌", "😴", "😷", "🤒", "😢", "😭", "😤", "😡", "😱", "😳", "🥺", "😬"],
  },
  {
    name: "Gestures",
    icon: "👍",
    emoji: ["👍", "👎", "👌", "✌️", "🤞", "🤝", "🙏", "👏", "🙌", "👋", "💪", "👉", "👈", "👆", "👇", "✋", "🤚", "🫡", "🤙", "✍️"],
  },
  {
    name: "Hearts",
    icon: "❤️",
    emoji: ["❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "💔", "💯", "✨", "🔥", "⭐", "🌟", "🎉", "🎊", "🎁", "🏆", "🥇", "✅", "❌", "⚠️", "❗", "❓"],
  },
  {
    name: "Objects",
    icon: "📱",
    emoji: ["📱", "☎️", "📞", "💬", "📩", "📧", "📄", "📎", "📌", "📍", "🗓️", "⏰", "⌛", "💰", "💳", "🧾", "🏠", "🏢", "🚗", "✈️", "🎂", "☕", "🍫", "🌹"],
  },
];

interface Props {
  onPick: (emoji: string) => void;
}

export function EmojiPicker({ onPick }: Props): JSX.Element {
  const [group, setGroup] = useState(0);
  const current = EMOJI_GROUPS[group] ?? EMOJI_GROUPS[0]!;
  return (
    <div role="dialog" aria-label="Emoji" className="w-[300px] rounded-lg border border-border bg-surface p-2 shadow-card">
      <div role="tablist" className="mb-2 flex gap-1 border-b border-border pb-1">
        {EMOJI_GROUPS.map((item, index) => (
          <button
            key={item.name}
            type="button"
            role="tab"
            aria-selected={index === group}
            title={item.name}
            onClick={() => setGroup(index)}
            className={`flex h-8 w-8 items-center justify-center rounded-md text-lg ${index === group ? "bg-[#ebf5f3] dark:bg-accent-soft" : "hover:bg-hover"}`}
          >
            {item.icon}
          </button>
        ))}
      </div>
      <div className="grid max-h-44 grid-cols-8 gap-0.5 overflow-y-auto">
        {current.emoji.map((emoji) => (
          <button
            key={emoji}
            type="button"
            aria-label={`Insert ${emoji}`}
            onClick={() => onPick(emoji)}
            className="flex h-8 w-8 items-center justify-center rounded-md text-xl hover:bg-hover"
          >
            {emoji}
          </button>
        ))}
      </div>
    </div>
  );
}
