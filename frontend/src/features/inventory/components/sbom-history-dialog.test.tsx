import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ARCHIVED_VERSION, SBOM } from "./sbom-fixtures";
import { SbomHistoryDialog } from "./sbom-history-dialog";

const CURRENT = { ...ARCHIVED_VERSION, id: 8, label: "v1.4.0", isCurrent: true };

describe("SbomHistoryDialog", () => {
  it("listet Versionen mit Status und meldet die Auswahl", async () => {
    const onSelect = vi.fn();
    render(
      <SbomHistoryDialog
        sbom={SBOM}
        versions={[CURRENT, ARCHIVED_VERSION]}
        selected={null}
        onSelect={onSelect}
        onOpenChange={vi.fn()}
      />,
    );
    expect(screen.getByTestId("inventory-item-sbom-version-8")).toHaveTextContent("aktuell");
    expect(screen.getByTestId("inventory-item-sbom-version-7")).toHaveTextContent("archiviert");

    await userEvent.click(screen.getByTestId("inventory-btn-sbom-version-7"));
    expect(onSelect).toHaveBeenCalledWith(7);
  });

  it("markiert nicht geprüfte Einträge über checked, auch mit Ökosystem", () => {
    const version = {
      ...ARCHIVED_VERSION,
      components: [{ ...ARCHIVED_VERSION.components[0]!, checked: false }],
    };
    render(
      <SbomHistoryDialog
        sbom={SBOM}
        versions={[version]}
        selected={version}
        onSelect={vi.fn()}
        onOpenChange={vi.fn()}
      />,
    );
    expect(screen.getByTestId("inventory-item-sbom-entry-0")).toHaveTextContent("npm");
    expect(screen.getByTestId("inventory-text-sbom-unchecked-0")).toHaveTextContent(
      "nicht geprüft",
    );
    expect(screen.getByTestId("inventory-btn-sbom-version-7")).toHaveAttribute(
      "aria-current",
      "true",
    );
  });

  it("zeigt die Komponenten der gewählten Version", () => {
    render(
      <SbomHistoryDialog
        sbom={SBOM}
        versions={[ARCHIVED_VERSION]}
        selected={ARCHIVED_VERSION}
        onSelect={vi.fn()}
        onOpenChange={vi.fn()}
      />,
    );
    const list = screen.getByTestId("inventory-list-sbom-components");
    expect(list).toHaveTextContent("react");
    expect(list).toHaveTextContent("pkg:deb/debian/openssl@3.0.11");
    expect(screen.getByTestId("inventory-text-sbom-unchecked-1")).toHaveTextContent(
      "nicht geprüft",
    );
  });
});
