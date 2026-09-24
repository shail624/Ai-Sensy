import { ArrowRight, PlaneTakeoff } from "lucide-react";
import { useState, type ChangeEvent } from "react";
import { useNavigate } from "react-router-dom";

import { Modal } from "@/components/ui";
import { api } from "@/lib/api/client";
import { apiErrorMessage, unwrap } from "@/lib/api/errors";

interface Choice {
  title: string;
  text: string;
  badge?: string;
  action: "broadcast" | "api" | "csv" | null;
}

const CHOICES: Choice[] = [
  {
    title: "Broadcast Campaign",
    text: "Select and filter among your existing audience & broadcast a customized template message.",
    action: "broadcast",
  },
  {
    title: "API Campaign",
    text: "Connect your existing systems with our API to send template messages automatically. Opens the Developer page for your API key.",
    action: "api",
  },
  {
    title: "CSV Broadcast",
    badge: "NEW",
    text: "Upload your audience from a CSV file & broadcast a customized template message to them.",
    action: "csv",
  },
  {
    title: "Meta Ads",
    badge: "SOON",
    text: "Click-to-WhatsApp ads on Facebook and Instagram. Not available in this app yet.",
    action: null,
  },
];

const NEXT =
  "inline-flex h-10 items-center gap-2 rounded-md bg-[var(--color-nav-bg)] px-4 text-sm font-medium text-white transition-colors hover:bg-[#08393d] disabled:cursor-not-allowed disabled:opacity-40";

/** The reference "Select Campaign Type" dialog shown by Launch. */
export function CampaignTypeDialog({ onClose }: { onClose: () => void }): JSX.Element {
  const navigate = useNavigate();
  const [csv, setCsv] = useState(false);

  if (csv) return <CsvBroadcastDialog onClose={onClose} onBack={() => setCsv(false)} />;

  function choose(action: Choice["action"]): void {
    if (action === "broadcast") navigate("/campaigns/new");
    else if (action === "api") navigate("/operations/api");
    else if (action === "csv") setCsv(true);
  }

  return (
    <Modal title="Select Campaign Type" onClose={onClose} panelClassName="!max-w-[760px] !rounded-md" contentClassName="!px-6">
      <div className="max-h-[70vh] space-y-4 overflow-y-auto pb-2">
        {CHOICES.map((choice) => (
          <div key={choice.title} className={`rounded-[8px] border border-[#e0e0e0] p-5 dark:border-border ${choice.action ? "" : "opacity-60"}`}>
            <div className="flex items-start justify-between gap-3">
              <h3 className="text-lg text-[var(--color-nav-bg)] dark:text-accent">{choice.title}</h3>
              {choice.badge ? <span className="text-xs font-bold text-[var(--color-nav-bg)] dark:text-accent">{choice.badge}</span> : null}
            </div>
            <p className="mt-2 text-sm text-[#6e6e6e] dark:text-text-secondary">{choice.text}</p>
            <div className="mt-4 flex justify-end">
              <button type="button" disabled={!choice.action} onClick={() => choose(choice.action)} className={NEXT} aria-label={`${choice.title}: next`}>
                Next <ArrowRight aria-hidden className="h-4 w-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </Modal>
  );
}

export interface CsvRow {
  phone: string;
  name: string | null;
}

/**
 * Read numbers (and names, when a column is called "name") from CSV text. The phone column is the
 * first one whose values look like phone numbers; a header row is detected and skipped.
 */
export function parseNumbersCsv(text: string): CsvRow[] {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => line.split(/[,;\t]/).map((cell) => cell.trim().replace(/^"|"$/g, "")));
  if (lines.length === 0) return [];
  const looksLikePhone = (cell: string) => /^\+?[\d\s()-]{8,}$/.test(cell);
  const first = lines[0]!;
  const hasHeader = !first.some(looksLikePhone);
  const header = hasHeader ? first.map((cell) => cell.toLowerCase()) : [];
  const body = hasHeader ? lines.slice(1) : lines;
  let phoneColumn = header.findIndex((cell) => /phone|mobile|number|whatsapp/.test(cell));
  if (phoneColumn < 0) phoneColumn = Math.max(0, (body[0] ?? []).findIndex(looksLikePhone));
  const nameColumn = header.findIndex((cell) => /name/.test(cell));
  return body
    .map((cells) => ({ phone: cells[phoneColumn] ?? "", name: nameColumn >= 0 ? cells[nameColumn] || null : null }))
    .filter((row) => row.phone !== "");
}

function CsvBroadcastDialog({ onClose, onBack }: { onClose: () => void; onBack: () => void }): JSX.Element {
  const navigate = useNavigate();
  const [rows, setRows] = useState<CsvRow[] | null>(null);
  const [fileName, setFileName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onFile(event: ChangeEvent<HTMLInputElement>): Promise<void> {
    const file = event.target.files?.[0];
    if (!file) return;
    setError(null);
    setFileName(file.name);
    const parsed = parseNumbersCsv(await file.text());
    setRows(parsed);
    if (parsed.length === 0) setError("No phone numbers found in this file.");
    else if (parsed.length > 5000) setError("Upload at most 5,000 numbers at a time.");
  }

  async function next(): Promise<void> {
    if (!rows?.length) return;
    setBusy(true);
    setError(null);
    try {
      const result = unwrap(await api.POST("/api/v1/contacts/resolve-numbers", { body: { rows } }));
      if (result.contact_ids.length === 0) {
        setError("None of the numbers could be read. Use 10-digit Indian numbers or include the country code.");
        return;
      }
      navigate("/campaigns/new", { state: { contactIds: result.contact_ids } });
    } catch (caught) {
      setError(apiErrorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title="CSV Broadcast" onClose={onClose} panelClassName="!max-w-[560px] !rounded-md" contentClassName="!px-6">
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-sm text-[#6e6e6e] dark:text-text-secondary">
          <PlaneTakeoff aria-hidden className="h-4 w-4 text-[var(--color-nav-bg)]" />
          Upload a CSV with a phone number column (a &quot;name&quot; column is optional). Up to 5,000 numbers.
        </div>
        <label className="flex cursor-pointer flex-col items-center gap-2 rounded-[8px] border-2 border-dashed border-[#c4c4c4] p-6 text-center text-sm hover:border-[var(--color-nav-bg)]">
          <span className="font-medium text-[var(--color-nav-bg)] dark:text-accent">{fileName || "Choose a CSV file"}</span>
          <span className="text-xs text-[#808080]">10-digit numbers are treated as Indian (+91).</span>
          <input type="file" accept=".csv,.txt,text/csv" aria-label="CSV file" className="sr-only" onChange={(event) => void onFile(event)} />
        </label>
        {rows && rows.length > 0 ? (
          <p className="text-sm text-black dark:text-text-primary">
            {rows.length.toLocaleString("en-IN")} numbers found. Next, pick the template and review before anything is sent.
          </p>
        ) : null}
        {error ? <p role="alert" className="rounded-md bg-danger-soft px-3 py-2 text-sm text-danger-on-soft">{error}</p> : null}
        <div className="flex justify-between gap-2 border-t border-border pt-3">
          <button type="button" onClick={onBack} className="h-9 rounded-md px-4 text-sm font-medium text-[#4a4a4a] hover:bg-hover dark:text-text-secondary">Back</button>
          <button type="button" disabled={!rows?.length || rows.length > 5000 || busy} onClick={() => void next()} className={NEXT}>
            {busy ? "Preparing audience…" : "Next"} <ArrowRight aria-hidden className="h-4 w-4" />
          </button>
        </div>
      </div>
    </Modal>
  );
}
