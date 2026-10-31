import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { App } from "./app";
import { Providers } from "./providers";

function renderApp() {
  return render(
    <Providers>
      <App />
    </Providers>,
  );
}

describe("App", () => {
  it("zeigt Kopfzeile, Inventar und Funde-Bereich", () => {
    renderApp();

    expect(screen.getByTestId("app-text-title")).toHaveTextContent("alarming-spooky-wraith");
    expect(screen.getByTestId("inventory-section-manage")).toBeInTheDocument();
    expect(screen.getByTestId("cves-section-overview")).toBeInTheDocument();
  });

  it("schaltet das dunkle Design um", async () => {
    renderApp();

    await userEvent.click(screen.getByTestId("app-btn-theme-toggle"));

    expect(document.documentElement).toHaveClass("dark");
  });
});
