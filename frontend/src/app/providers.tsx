import type { ReactNode } from "react";
import { type QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { createQueryClient } from "./query-client";

const appQueryClient = createQueryClient();

interface ProvidersProps {
  children: ReactNode;
  /** Nur für Tests: eigener Client, damit kein Cache zwischen Tests überlebt. */
  client?: QueryClient;
}

export function Providers({ children, client = appQueryClient }: ProvidersProps) {
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
