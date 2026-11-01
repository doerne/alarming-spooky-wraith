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
  it("zeigt standardmaessig das Schwachstellen-Dashboard", () => {
    renderApp();

    expect(screen.getByTestId("app-text-title")).toHaveTextContent("Schwachstellen");
    expect(screen.getByTestId("cves-section-overview")).toBeInTheDocument();
  });

  it("wechselt ueber die Navigation zum Inventar", async () => {
    renderApp();

    await userEvent.click(screen.getByTestId("app-btn-nav-inventory"));

    expect(screen.getByTestId("inventory-section-manage")).toBeInTheDocument();
  });

  it("wechselt ueber die Navigation zu den Quellen", async () => {
    renderApp();

    await userEvent.click(screen.getByTestId("app-btn-nav-sources"));

    expect(screen.getByTestId("app-text-title")).toHaveTextContent("Quellen");
    expect(screen.getByTestId("sources-section-overview")).toBeInTheDocument();
  });

  it("schaltet das dunkle Design um", async () => {
    renderApp();

    await userEvent.click(screen.getByTestId("app-btn-theme-toggle"));

    expect(document.documentElement).toHaveClass("dark");
  });
});
