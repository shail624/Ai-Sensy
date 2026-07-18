import { createBrowserRouter } from "react-router-dom";

import { AppShell } from "@/pages/AppShell";
import { ContactProfilePage } from "@/pages/ContactProfilePage";
import { ContactsPage } from "@/pages/ContactsPage";
import { NotFound } from "@/pages/NotFound";

// Application routes (React Router). Auth routes (login/forgot/reset) and protected
// routing with permission guards (Doc 05 B1 / DS-20) are added in later steps.
export const router = createBrowserRouter([
  { path: "/", element: <AppShell /> },
  { path: "/contacts", element: <ContactsPage /> },
  { path: "/contacts/:contactId", element: <ContactProfilePage /> },
  { path: "*", element: <NotFound /> },
]);
