import { useParams } from "react-router-dom";

import { CustomerProfile } from "@/features/customer-profile";
import { TasksSectionForProfile } from "@/features/tasks";

/** Route page: resolves the contact id from the URL and renders the reusable profile. */
export function ContactProfilePage(): JSX.Element {
  const { contactId } = useParams<{ contactId: string }>();
  if (!contactId) {
    return <div className="p-6 text-sm text-text-secondary">No contact selected.</div>;
  }
  // Tasks attach through the profile's designed extension slot (Doc 14 §9) — no existing section
  // is modified.
  return (
    <CustomerProfile
      contactId={contactId}
      extensionSlot={<TasksSectionForProfile contactId={contactId} />}
    />
  );
}
