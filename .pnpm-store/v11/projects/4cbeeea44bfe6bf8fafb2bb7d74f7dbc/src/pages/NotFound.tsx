import { Link } from "react-router-dom";

// 404 route (Doc 05 DS-18 — friendly full-page error state).
export function NotFound(): JSX.Element {
  return (
    <div className="flex min-h-full flex-col items-center justify-center gap-3 bg-canvas px-6 text-center text-text-primary">
      <p className="text-sm font-semibold text-accent">404</p>
      <h1 className="text-2xl font-bold">Page not found</h1>
      <p className="text-text-secondary">The page you are looking for does not exist.</p>
      <Link
        to="/"
        className="mt-2 rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-fg hover:opacity-90 focus-visible:ring-2 focus-visible:ring-focus"
      >
        Back to home
      </Link>
    </div>
  );
}
