import { useState, type FormEvent } from "react";

import { Button, Field, Input, Modal } from "@/components/ui";
import { useCreateContact } from "@/features/contacts/api";
import { apiErrorMessage } from "@/lib/api/errors";

export function CreateContactDialog({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }): JSX.Element {
  const create = useCreateContact();
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [source, setSource] = useState("manual");
  const [validation, setValidation] = useState("");

  function submit(event: FormEvent): void {
    event.preventDefault();
    if (create.isPending) return;
    if (!name.trim() || !/^\+[1-9]\d{7,14}$/.test(phone.trim())) {
      setValidation("Enter a name and a valid international mobile number, such as +919876543210.");
      return;
    }
    setValidation("");
    create.mutate({ full_name: name.trim(), phone_e164: phone.trim(), source: source.trim() || "manual", opt_in_status: "unknown" }, { onSuccess: onCreated });
  }

  return (
    <Modal title="Create Contact" variant="sheet" onClose={() => { if (!create.isPending) onClose(); }}>
      <form onSubmit={submit} className="space-y-5" noValidate>
        <Field htmlFor="new-contact-name" label="Name *">
          <Input id="new-contact-name" autoFocus required maxLength={160} placeholder="User name" value={name} onChange={(event) => setName(event.target.value)} disabled={create.isPending} />
        </Field>
        <Field htmlFor="new-contact-phone" label="Mobile Number *">
          <Input id="new-contact-phone" type="tel" required placeholder="+919876543210" value={phone} onChange={(event) => setPhone(event.target.value)} disabled={create.isPending} aria-describedby="new-contact-phone-help" />
          <p id="new-contact-phone-help" className="mt-1 text-xs text-text-muted">Include + and the country code, followed by the mobile number.</p>
        </Field>
        <Field htmlFor="new-contact-source" label="Source">
          <Input id="new-contact-source" maxLength={40} value={source} onChange={(event) => setSource(event.target.value)} disabled={create.isPending} />
        </Field>
        <p className="text-sm text-text-secondary">Creating a contact does not grant messaging consent. Opt-in remains unknown.</p>
        {validation || create.error ? <p role="alert" className="text-sm text-danger">{validation || apiErrorMessage(create.error)}</p> : null}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" disabled={create.isPending} onClick={onClose}>Cancel</Button>
          <Button type="submit" loading={create.isPending}>Add Contact</Button>
        </div>
      </form>
    </Modal>
  );
}
