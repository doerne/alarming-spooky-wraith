import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SbomDeleteDialog } from "./sbom-delete-dialog";
import { SBOM } from "./sbom-fixtures";

describe("SbomDeleteDialog", () => {
  it("nennt die betroffenen Komponenten und bestätigt", async () => {
    const onConfirm = vi.fn();
    render(
      <SbomDeleteDialog
        sbom={SBOM}
        isDeleting={false}
        error={null}
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByTestId("inventory-dialog-sbom-delete")).toHaveTextContent("412 Komponenten");
    await userEvent.click(screen.getByTestId("inventory-btn-sbom-delete-confirm"));
    expect(onConfirm).toHaveBeenCalledWith(SBOM);
  });

  it("zeigt einen Fehler beim Löschen", () => {
    render(
      <SbomDeleteDialog
        sbom={SBOM}
        isDeleting={false}
        error="Anfrage fehlgeschlagen (500)"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByTestId("inventory-error-sbom-delete")).toHaveTextContent("500");
  });
});
