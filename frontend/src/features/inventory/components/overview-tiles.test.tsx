import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { OverviewTiles } from "./overview-tiles";

const COUNTS = { critical: 2, overdue: 0, sbom: 1, unscanned: 0 };

describe("OverviewTiles", () => {
  it("hebt brennende Werte rot und Pflege-Werte mit Icon hervor", () => {
    render(<OverviewTiles counts={COUNTS} active={null} onToggle={vi.fn()} />);
    expect(screen.getByTestId("inventory-text-tile-critical")).toHaveTextContent("2");
    expect(screen.getByTestId("inventory-text-tile-critical")).toHaveClass("text-destructive");
    expect(screen.getByTestId("inventory-text-tile-overdue")).not.toHaveClass("text-destructive");
    expect(screen.getByTestId("inventory-card-tile-sbom").querySelector("svg")).not.toBeNull();
    expect(screen.getByTestId("inventory-card-tile-unscanned").querySelector("svg")).toBeNull();
  });

  it("meldet den Klick und markiert die aktive Kachel", async () => {
    const onToggle = vi.fn();
    render(<OverviewTiles counts={COUNTS} active="sbom" onToggle={onToggle} />);
    await userEvent.click(screen.getByTestId("inventory-btn-tile-sbom"));
    expect(onToggle).toHaveBeenCalledWith("sbom");
    expect(screen.getByTestId("inventory-btn-tile-sbom")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("inventory-btn-tile-critical")).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("legt den Button in die Karte, nicht umgekehrt", () => {
    render(<OverviewTiles counts={COUNTS} active={null} onToggle={vi.fn()} />);
    const card = screen.getByTestId("inventory-card-tile-sbom");
    expect(card.querySelector("[data-testid='inventory-btn-tile-sbom']")).not.toBeNull();
  });
});
