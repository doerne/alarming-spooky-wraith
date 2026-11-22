import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CreateApplicationDialog } from "./create-application-dialog";

describe("CreateApplicationDialog", () => {
  it("legt eine Anwendung mit Namen an", async () => {
    const onCreate = vi.fn();
    render(
      <CreateApplicationDialog
        open
        onOpenChange={vi.fn()}
        onCreate={onCreate}
        isCreating={false}
        error={null}
      />,
    );
    expect(screen.getByTestId("inventory-dialog-create-app")).toBeInTheDocument();
    await userEvent.type(screen.getByTestId("inventory-input-app-name"), "Shop");
    await userEvent.click(screen.getByTestId("inventory-btn-create-app"));
    expect(onCreate.mock.calls[0]?.[0]).toEqual({ name: "Shop" });
  });

  it("sperrt das Absenden während des Anlegens und zeigt Fehler", () => {
    render(
      <CreateApplicationDialog
        open
        onOpenChange={vi.fn()}
        onCreate={vi.fn()}
        isCreating
        error="Anfrage fehlgeschlagen (500)"
      />,
    );
    expect(screen.getByTestId("inventory-btn-create-app")).toBeDisabled();
    expect(screen.getByTestId("inventory-error-create-app")).toHaveTextContent("500");
  });
});
