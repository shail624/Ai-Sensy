import { MessageSquareText, Workflow } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { PageContainer, PageHeader } from "@/components/layout";
import { Button } from "@/components/ui";
import { OperationalDashboard } from "@/features/dashboard";
import { useAuth, useHasPermission } from "@/lib/auth";

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export function DashboardPage(): JSX.Element {
  const navigate = useNavigate();
  const { user } = useAuth();
  const canInbox = useHasPermission("inbox:read");
  const canReactivation = useHasPermission("reactivation:read");
  const firstName = user?.full_name.trim().split(/\s+/)[0] ?? "there";

  return (
    <PageContainer>
      <PageHeader
        eyebrow="Daily operations"
        title="Operations desk"
        description={`${greeting()}, ${firstName}. Start with blocked customers, breached service work, waiting conversations and today’s KPI changes.`}
        meta={
          <>
            <span>Real authorized tenant data</span>
            <span>Decision-first operational view</span>
          </>
        }
        actions={
          <>
            {canInbox ? (
              <Button
                variant="secondary"
                leftIcon={<MessageSquareText aria-hidden className="h-4 w-4" />}
                onClick={() => navigate("/inbox")}
              >
                Open live chat
              </Button>
            ) : null}
            {canReactivation ? (
              <Button
                leftIcon={<Workflow aria-hidden className="h-4 w-4" />}
                onClick={() => navigate("/reactivation/pipeline")}
              >
                Open Reactivation
              </Button>
            ) : null}
          </>
        }
      />
      <OperationalDashboard />
    </PageContainer>
  );
}
