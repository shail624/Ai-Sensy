import { useState, type FormEvent, type ReactNode } from "react";

import { Modal } from "@/components/ui";
import { useUpdateBusinessProfile } from "@/features/channels/api";
import {
  VERTICAL_LABELS,
  type BusinessProfile,
  type BusinessProfileUpdateRequest,
  type BusinessVertical,
} from "@/features/channels/types";
import { apiErrorMessage } from "@/lib/api/errors";

import { DASH_PRIMARY_BUTTON } from "./dashboardStyles";

const INPUT =
  "h-[41px] w-full rounded-md bg-[#f5f5f5] px-3 text-sm text-text-primary placeholder:text-text-disabled transition-shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus dark:bg-surface-2";

function Row({ id, label, help, children }: { id: string; label: string; help: string; children: ReactNode }): JSX.Element {
  return (
    <div className="grid gap-3 border-b border-[#f0f0f0] py-4 last:border-b-0 dark:border-border sm:grid-cols-[1fr_336px]">
      <div>
        <label htmlFor={id} className="text-base font-medium text-text-primary">{label}</label>
        <p className="mt-1 text-xs leading-[17px] text-[#6e6e6e] dark:text-text-secondary">{help}</p>
      </div>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

interface EditBusinessProfileDialogProps {
  numberId: string;
  profile: BusinessProfile;
  onClose: () => void;
}

/** AiSensy's pencil dialog: edit the public WhatsApp Business profile, written straight to Meta. */
export function EditBusinessProfileDialog({ numberId, profile, onClose }: EditBusinessProfileDialogProps): JSX.Element {
  const update = useUpdateBusinessProfile();
  const [description, setDescription] = useState(profile.description ?? "");
  const [address, setAddress] = useState(profile.address ?? "");
  const [email, setEmail] = useState(profile.email ?? "");
  const [vertical, setVertical] = useState(profile.vertical ?? "");
  const [sites, setSites] = useState<[string, string]>([(profile.websites ?? [])[0] ?? "", (profile.websites ?? [])[1] ?? ""]);

  function changes(): BusinessProfileUpdateRequest {
    const body: BusinessProfileUpdateRequest = {};
    if (description !== (profile.description ?? "")) body.description = description;
    if (address !== (profile.address ?? "")) body.address = address;
    if (email !== (profile.email ?? "")) body.email = email;
    if (vertical && vertical !== (profile.vertical ?? "")) body.vertical = vertical as BusinessVertical;
    const websites = sites.map((site) => site.trim()).filter(Boolean);
    if (websites.join("\n") !== (profile.websites ?? []).join("\n")) body.websites = websites;
    return body;
  }

  function submit(event: FormEvent): void {
    event.preventDefault();
    const body = changes();
    if (Object.keys(body).length === 0) {
      onClose();
      return;
    }
    update.mutate({ numberId, body }, { onSuccess: onClose });
  }

  return (
    <Modal title="Edit Business Profile" onClose={onClose} panelClassName="!max-w-[767px] !rounded-md" contentClassName="!px-6">
      <form onSubmit={submit} noValidate>
        <Row id="bp-description" label="Description" help="Description of the business. Maximum of 512 characters.">
          <textarea id="bp-description" value={description} maxLength={512} rows={3} placeholder="Enter Description" onChange={(e) => setDescription(e.target.value)} className={`${INPUT} h-auto min-h-[41px] py-2.5`} />
        </Row>
        <Row id="bp-address" label="Address" help="Address of the business. Maximum of 256 characters.">
          <input id="bp-address" value={address} maxLength={256} placeholder="Enter Address" onChange={(e) => setAddress(e.target.value)} className={INPUT} />
        </Row>
        <Row id="bp-email" label="Email" help="Email address (in valid email format) to contact the business. Maximum of 128 characters.">
          <input id="bp-email" type="email" value={email} maxLength={128} placeholder="Enter Email" onChange={(e) => setEmail(e.target.value)} className={INPUT} />
        </Row>
        <Row id="bp-vertical" label="Vertical" help="Industry of the business.">
          <select id="bp-vertical" value={vertical} onChange={(e) => setVertical(e.target.value)} className={INPUT}>
            <option value="" disabled>Select Vertical</option>
            {Object.entries(VERTICAL_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </Row>
        <Row id="bp-website-1" label="Websites" help="URLs (including http:// or https://) associated with the business. Maximum of 2 websites.">
          {sites.map((site, index) => (
            <input
              key={index}
              id={`bp-website-${index + 1}`}
              aria-label={`Website ${index + 1}`}
              type="url"
              value={site}
              maxLength={256}
              placeholder="Enter Website"
              onChange={(e) => setSites((current) => (index === 0 ? [e.target.value, current[1]] : [current[0], e.target.value]))}
              className={INPUT}
            />
          ))}
        </Row>

        {update.isError ? (
          <p role="alert" className="mt-2 rounded-md bg-danger-soft px-3 py-2 text-sm text-danger-on-soft">
            {apiErrorMessage(update.error)}
          </p>
        ) : null}

        <div className="flex justify-end gap-2 pb-2 pt-4">
          <button type="button" onClick={onClose} className="h-9 rounded-md px-4 text-sm font-medium text-[#4a4a4a] transition-colors hover:bg-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus dark:text-text-secondary">
            Cancel
          </button>
          <button type="submit" disabled={update.isPending} className={`${DASH_PRIMARY_BUTTON} !h-[37px] px-4 text-sm disabled:opacity-60`}>
            {update.isPending ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
