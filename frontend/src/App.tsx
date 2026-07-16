import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";

import { queryClient } from "@/lib/queryClient";
import { ThemeProvider } from "@/lib/theme";
import { router } from "@/routes/router";

// Root composition: theme (dark mode) + data-fetching + routing providers (Doc 05).
export function App(): JSX.Element {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </ThemeProvider>
  );
}
