import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useCreateApplication } from "./use-create-application";

afterEach(() => vi.restoreAllMocks());

describe("useCreateApplication", () => {
  it("lädt Liste und Übersicht nach dem Anlegen neu", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ id: 4, name: "Shop", description: "" }), { status: 201 }),
    );
    const client = new QueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
    const { result } = renderHook(() => useCreateApplication(), { wrapper });

    await act(() => result.current.mutateAsync({ name: "Shop" }));

    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["applications"] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["findings", "applications-overview"] });
  });
});
