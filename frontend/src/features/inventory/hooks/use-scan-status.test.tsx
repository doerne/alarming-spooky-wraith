import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useScanStatus } from "./use-scan-status";

function statusBody(running: boolean) {
  return {
    running,
    startedAt: running ? "2026-11-22T09:00:00Z" : null,
    finishedAt: null,
    componentsScanned: null,
    findingsFound: null,
    error: null,
    lastRun: null,
    lastUsableRun: null,
    steps: [],
  };
}

afterEach(() => vi.restoreAllMocks());

describe("useScanStatus (Inventar)", () => {
  it("lädt nach Ende eines Scans auch die Übersicht neu", async () => {
    const responses = [statusBody(true), statusBody(false)];
    vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      Promise.resolve(new Response(JSON.stringify(responses.shift() ?? statusBody(false)))),
    );
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );

    renderHook(() => useScanStatus(10), { wrapper });

    await waitFor(() =>
      expect(invalidate).toHaveBeenCalledWith({ queryKey: ["findings", "applications-overview"] }),
    );
  });
});
