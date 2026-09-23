import { Plus } from "lucide-react";
import { Link } from "react-router-dom";

import { MANAGE_PRIMARY_ACTION, ManagePageHeader } from "@/components/layout";
import { TemplateList } from "@/features/templates";
import { useHasPermission } from "@/lib/auth";

/** Route page for the Templates module (Doc 05 B5.1), laid out as the reference's Manage page. */
export function TemplatesPage(): JSX.Element {
  const canWrite = useHasPermission("templates:write");
  return (
    <div className="min-h-full bg-[#f9f9f9] dark:bg-canvas">
      <ManagePageHeader
        title="Template Messages"
        actions={
          canWrite ? (
            <Link to="/templates/new" className={`${MANAGE_PRIMARY_ACTION} gap-2`}>
              <Plus aria-hidden className="h-[18px] w-[18px]" />
              Create Template
            </Link>
          ) : null
        }
      />
      <div className="px-4 py-6 sm:px-[45px]">
        <TemplateList />
      </div>
    </div>
  );
}
