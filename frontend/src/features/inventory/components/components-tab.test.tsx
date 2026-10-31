import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Component } from "../model/types";
import { ComponentsTab } from "./components-tab";

const component: Component = {
  id: 10,
  applicationId: 1,
  name: "react",
  version: "18.2.0",
  category: "library",
  ecosystem: "npm",
  direct: true,
};

function renderTab(editing: Component | null) {
  const handlers = { onEdit: vi.fn(), onSubmit: vi.fn(), onCancelEdit: vi.fn() };
  render(
    <ComponentsTab components={[component]} editing={editing} isSubmitting={false} {...handlers} />,
  );
  return handlers;
}

describe("ComponentsTab", () => {
  it("zeigt im Anlege-Modus die Hinzufügen-Überschrift und keinen Abbrechen-Button", () => {
    renderTab(null);

    expect(screen.getByTestId("inventory-text-form-title")).toHaveTextContent("hinzufügen");
    expect(screen.queryByTestId("inventory-btn-cancel")).not.toBeInTheDocument();
  });

  it("füllt im Bearbeiten-Modus das Formular vor und kann abbrechen", async () => {
    const handlers = renderTab(component);

    expect(screen.getByTestId("inventory-text-form-title")).toHaveTextContent("bearbeiten");
    expect(screen.getByTestId("inventory-input-version")).toHaveValue("18.2.0");

    await userEvent.click(screen.getByTestId("inventory-btn-cancel"));
    expect(handlers.onCancelEdit).toHaveBeenCalled();
  });
});
