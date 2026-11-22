import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { useRefreshAfterSync } from "./use-github";

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
