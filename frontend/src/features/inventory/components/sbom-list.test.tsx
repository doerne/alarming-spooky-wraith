import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SBOM } from "./sbom-fixtures";
import { SbomList } from "./sbom-list";

function renderList(sboms = [SBOM]) {
  const handlers = { onUploadVersion: vi.fn(), onShowHistory: vi.fn(), onDelete: vi.fn() };
  render(<SbomList sboms={sboms} {...handlers} />);
  return handlers;
}

describe("SbomList", () => {
  it("zeigt Name, aktuelle Version und nicht geprüfte Komponenten", () => {
    renderList();
    const item = screen.getByTestId("inventory-item-sbom-3");
    expect(item).toHaveTextContent("backend-image");
    expect(item).toHaveTextContent("v1.4.0");
    expect(item).toHaveTextContent("412 Komponenten");
    expect(item).toHaveTextContent("318 nicht geprüft");
    expect(item).toHaveTextContent("2 Versionen");
  });

  it("meldet Aktionen für die SBOM", async () => {
    const handlers = renderList();
    await userEvent.click(screen.getByTestId("inventory-btn-sbom-new-version-3"));
    await userEvent.click(screen.getByTestId("inventory-btn-sbom-history-3"));
    await userEvent.click(screen.getByTestId("inventory-btn-sbom-delete-3"));
    expect(handlers.onUploadVersion).toHaveBeenCalledWith(SBOM);
    expect(handlers.onShowHistory).toHaveBeenCalledWith(SBOM);
    expect(handlers.onDelete).toHaveBeenCalledWith(SBOM);
  });

  it("benennt die Aktionen für Screenreader", () => {
    renderList();
    expect(screen.getByTestId("inventory-btn-sbom-new-version-3")).toHaveAccessibleName(
      "Neue Version von backend-image",
    );
    expect(screen.getByTestId("inventory-btn-sbom-history-3")).toHaveAccessibleName(
      "Verlauf von backend-image",
    );
  });

  it("zeigt einen Hinweis ohne SBOMs", () => {
    renderList([]);
    expect(screen.getByTestId("inventory-text-no-sboms")).toHaveTextContent(
      "Noch keine SBOM hinterlegt.",
    );
  });
});
