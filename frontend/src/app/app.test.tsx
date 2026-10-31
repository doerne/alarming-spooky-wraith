import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { App } from "./app";

describe("App", () => {
  it("zeigt Kopfzeile und Startseite", () => {
    render(<App />);

    expect(screen.getByTestId("app-text-title")).toHaveTextContent("alarming-spooky-wraith");
    expect(screen.getByTestId("home-card-welcome")).toBeInTheDocument();
  });

  it("schaltet das dunkle Design um", async () => {
    render(<App />);

    await userEvent.click(screen.getByTestId("app-btn-theme-toggle"));

    expect(document.documentElement).toHaveClass("dark");
  });
});
