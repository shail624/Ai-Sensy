import { useParams } from "react-router-dom";

import { CustomerProfile } from "@/features/customer-profile";

/** Route page: resolves the contact id from the URL and renders the reusable profile. */
export function ContactProfilePage(): JSX.Element {
  const { contactId } = useParams<{ contactId: string }>();
  if (!contactId) {
    return <div className="p-6 text-sm text-text-secondary">No contact selected.</div>;
  }
  return <CustomerProfile contactId={contactId} />;
}
