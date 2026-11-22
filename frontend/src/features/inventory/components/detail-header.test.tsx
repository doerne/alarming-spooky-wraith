import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DetailHeader } from "./detail-header";

describe("DetailHeader", () => {
  it("sperrt das Löschen, solange die Anwendung nicht geladen ist", () => {
    render(<DetailHeader name="Anwendung" onBack={vi.fn()} actions={null} onDelete={null} />);
    expect(screen.getByTestId("inventory-btn-delete-app")).toBeDisabled();
  });

  it("öffnet das Löschen per Klick", async () => {
    const onDelete = vi.fn();
    render(<DetailHeader name="Shop" onBack={vi.fn()} actions={null} onDelete={onDelete} />);
    await userEvent.click(screen.getByTestId("inventory-btn-delete-app"));
    expect(onDelete).toHaveBeenCalledOnce();
  });

  it("kennzeichnet das Löschen als destruktiv", () => {
    render(<DetailHeader name="Shop" onBack={vi.fn()} actions={null} onDelete={vi.fn()} />);
    expect(screen.getByTestId("inventory-btn-delete-app")).toHaveAttribute(
      "data-variant",
      "destructive",
    );
  });
});
