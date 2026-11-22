import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Component } from "../model/types";
import { ComponentTable } from "./component-table";

const components: Component[] = [
  {
    id: 10,
    applicationId: 1,
    name: "react",
    version: "18.2.0",
    category: "library",
    ecosystem: "npm",
    direct: true,
    sbomId: null,
    checked: true,
  },
];

const NO_SBOMS: ReadonlyMap<number, string> = new Map();

const sbomComponent: Component = {
  id: 11,
  applicationId: 1,
  name: "openssl",
  version: "3.0.11",
  category: "library",
  ecosystem: null,
  direct: false,
  sbomId: 3,
  checked: false,
};

describe("ComponentTable", () => {
  it("zeigt manuelle Komponenten als manuell und bearbeitbar", () => {
    render(<ComponentTable components={components} sbomNames={NO_SBOMS} onEdit={vi.fn()} />);

    expect(screen.getByTestId("inventory-item-component-10")).toHaveTextContent("manuell");
    expect(screen.getByTestId("inventory-btn-edit-10")).toBeInTheDocument();
    expect(screen.queryByTestId("inventory-text-unchecked-10")).not.toBeInTheDocument();
  });

  it("zeigt SBOM-Komponenten mit Quelle, ohne Bearbeiten und mit Hinweis", () => {
    render(
      <ComponentTable
        components={[sbomComponent]}
        sbomNames={new Map([[3, "backend-image"]])}
        onEdit={vi.fn()}
      />,
    );

    expect(screen.getByTestId("inventory-item-component-11")).toHaveTextContent("backend-image");
    expect(screen.queryByTestId("inventory-btn-edit-11")).not.toBeInTheDocument();
    expect(screen.getByTestId("inventory-text-unchecked-11")).toHaveTextContent("nicht geprüft");
  });

  it("zeigt SBOM als Quelle, wenn der Name noch nicht geladen ist", () => {
    render(<ComponentTable components={[sbomComponent]} sbomNames={NO_SBOMS} onEdit={vi.fn()} />);

    expect(screen.getByTestId("inventory-item-component-11")).toHaveTextContent("SBOM");
  });

  it("zeigt die Komponenten einer Anwendung", () => {
    render(<ComponentTable components={components} sbomNames={NO_SBOMS} onEdit={vi.fn()} />);

    const row = screen.getByTestId("inventory-item-component-10");
    expect(row).toHaveTextContent("react");
    expect(row).toHaveTextContent("18.2.0");
  });

  it("meldet die zu bearbeitende Komponente", async () => {
    const onEdit = vi.fn();
    render(<ComponentTable components={components} sbomNames={NO_SBOMS} onEdit={onEdit} />);

    await userEvent.click(screen.getByTestId("inventory-btn-edit-10"));

    expect(onEdit).toHaveBeenCalledWith(components[0]);
  });

  it("zeigt einen Hinweis bei leerer Liste", () => {
    render(<ComponentTable components={[]} sbomNames={NO_SBOMS} onEdit={vi.fn()} />);

    expect(screen.getByTestId("inventory-text-no-components")).toBeInTheDocument();
  });
});
