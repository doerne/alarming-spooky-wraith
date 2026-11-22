import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DeleteApplicationDialog } from "./delete-application-dialog";

const COUNTS = { components: 12, sboms: 2, findings: 7 };

interface DialogOverrides {
  error?: string | null;
  isDeleting?: boolean;
  onConfirm?: () => void;
  onCancel?: () => void;
}

function renderDialog(overrides: DialogOverrides = {}) {
  render(
    <DeleteApplicationDialog
      name="Shop"
      counts={COUNTS}
      isDeleting={overrides.isDeleting ?? false}
      error={overrides.error ?? null}
      onConfirm={overrides.onConfirm ?? vi.fn()}
      onCancel={overrides.onCancel ?? vi.fn()}
    />,
  );
}

describe("DeleteApplicationDialog", () => {
  it("nennt Name und Anzahl der betroffenen Daten", () => {
    renderDialog();
    const dialog = screen.getByTestId("inventory-dialog-delete-app");
    expect(dialog).toHaveTextContent("Shop löschen?");
    expect(dialog).toHaveTextContent(
      "Shop mit 12 Komponenten, 2 SBOMs und 7 Funden endgültig löschen?",
    );
    expect(dialog).toHaveTextContent(
      "Bereits angelegte GitHub-Issues bleiben auf GitHub bestehen.",
    );
  });

  it("ruft beim Bestätigen onConfirm auf", async () => {
    const onConfirm = vi.fn();
    renderDialog({ onConfirm });
    const confirm = screen.getByTestId("inventory-btn-confirm-delete-app");
    expect(confirm).toHaveTextContent("Endgültig löschen");
    await userEvent.click(confirm);
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it("zeigt einen Fehler beim Löschen", () => {
    renderDialog({
      error: "Während eines Scans oder GitHub-Abgleichs kann nicht gelöscht werden.",
    });
    expect(screen.getByTestId("inventory-error-delete-app")).toHaveTextContent(
      "Während eines Scans",
    );
  });

  it("bricht über Abbrechen ab", async () => {
    const onCancel = vi.fn();
    renderDialog({ onCancel });
    await userEvent.click(screen.getByTestId("inventory-btn-cancel-delete-app"));
    expect(onCancel).toHaveBeenCalled();
  });

  it("sperrt das Bestätigen während des Löschens", () => {
    renderDialog({ isDeleting: true });
    expect(screen.getByTestId("inventory-btn-confirm-delete-app")).toBeDisabled();
  });
});
