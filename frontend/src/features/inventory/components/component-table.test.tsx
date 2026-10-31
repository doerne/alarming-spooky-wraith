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
  },
];

describe("ComponentTable", () => {
  it("zeigt die Komponenten einer Anwendung", () => {
    render(<ComponentTable components={components} onEdit={vi.fn()} />);

    const row = screen.getByTestId("inventory-item-component-10");
    expect(row).toHaveTextContent("react");
    expect(row).toHaveTextContent("18.2.0");
  });

  it("meldet die zu bearbeitende Komponente", async () => {
    const onEdit = vi.fn();
    render(<ComponentTable components={components} onEdit={onEdit} />);

    await userEvent.click(screen.getByTestId("inventory-btn-edit-10"));

    expect(onEdit).toHaveBeenCalledWith(components[0]);
  });

  it("zeigt einen Hinweis bei leerer Liste", () => {
    render(<ComponentTable components={[]} onEdit={vi.fn()} />);

    expect(screen.getByTestId("inventory-text-no-components")).toBeInTheDocument();
  });
});
