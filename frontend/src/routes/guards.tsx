import type { ReactNode } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { EmptyState, Spinner } from "@/components/ui";
import { useAuth } from "@/lib/auth";

function BootstrapSplash(): JSX.Element {
  return (
    <div className="flex h-screen items-center justify-center bg-canvas">
      <Spinner label="Restoring your session…" />
    </div>
  );
}

/**
 * Gate for every authenticated route (Doc 05 B1 / DS-20). While the session bootstraps it holds the
 * splash rather than redirecting, so a reload never bounces a signed-in user to the login page. The
 * attempted location is preserved so login can return there.
 */
export function RequireAuth(): JSX.Element {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "loading") return <BootstrapSplash />;
  if (status === "anonymous") {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return <Outlet />;
}

/** Keeps a signed-in user out of /login. */
export function RequireAnonymous(): JSX.Element {
  const { status } = useAuth();
  if (status === "loading") return <BootstrapSplash />;
  if (status === "authenticated") return <Navigate to="/" replace />;
  return <Outlet />;
}

/**
 * Route-level permission gate backed by `MeResponse.permissions`. A user who is signed in but not
 * entitled gets an honest "not available" surface rather than a redirect loop or a raw 403.
 */
export function RequirePermission({
  code,
  children,
}: {
  code: string;
  children?: ReactNode;
}): JSX.Element {
  const { hasPermission } = useAuth();

  if (!hasPermission(code)) {
    return (
      <div className="p-6">
        <EmptyState
          title="You don't have access to this area"
          description="Ask an administrator if you need access."
        />
      </div>
    );
  }
  return <>{children ?? <Outlet />}</>;
}

/** Area-level gate where child sections intentionally enforce different existing permissions. */
export function RequireAnyPermission({ codes }: { codes: string[] }): JSX.Element {
  const { hasPermission } = useAuth();
  if (!codes.some((code) => hasPermission(code))) {
    return (
      <div className="p-6">
        <EmptyState title="You don't have access to this area" description="Ask an administrator if you need access." />
      </div>
    );
  }
  return <Outlet />;
}
