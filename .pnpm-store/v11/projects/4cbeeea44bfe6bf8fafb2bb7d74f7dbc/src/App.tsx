import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";

import { AuthProvider } from "@/lib/auth";
import { queryClient } from "@/lib/queryClient";
import { ThemeProvider } from "@/lib/theme";
import { router } from "@/routes/router";

// Root composition: theme (dark mode) + data-fetching + session + routing providers (Doc 05).
// AuthProvider sits inside QueryClientProvider because signing out clears the query cache.
export function App(): JSX.Element {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
