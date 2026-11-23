import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useRefreshAfterSync, useUpdateGitHubSettings } from "./use-github";

afterEach(() => vi.restoreAllMocks());

describe("useRefreshAfterSync", () => {
  it("lädt nach Ende des Abgleichs Anwendung, Funde und Verlauf neu", () => {
    const client = new QueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
    const { rerender } = renderHook(({ running }) => useRefreshAfterSync(7, running), {
      wrapper,
      initialProps: { running: true },
    });
    expect(invalidate).not.toHaveBeenCalled();

    rerender({ running: false });

    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["application", 7] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["application-findings", 7] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["findings"] });
  });
});

describe("useUpdateGitHubSettings", () => {
  it("lädt Anwendung und Übersicht nach dem Speichern neu", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 204 }));
    const client = new QueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
    const { result } = renderHook(() => useUpdateGitHubSettings(7), { wrapper });

    await act(() =>
      result.current.mutateAsync({ githubRepository: "acme/shop", autoIssueMinLevel: null }),
    );

    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["application", 7] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["findings", "applications-overview"] });
  });
});
