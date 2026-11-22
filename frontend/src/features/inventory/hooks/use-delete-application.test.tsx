import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useDeleteApplication } from "./use-delete-application";

afterEach(() => vi.restoreAllMocks());

describe("useDeleteApplication", () => {
  it("lädt Listen neu und markiert die gelöschte Anwendung nur als veraltet", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 204 }));
    const client = new QueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
    const { result } = renderHook(() => useDeleteApplication(7), { wrapper });

    await act(() => result.current.mutateAsync());

    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["applications"] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["findings"] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["application", 7], refetchType: "none" });
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: ["application-findings", 7],
      refetchType: "none",
    });
  });
});
