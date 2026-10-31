import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { InventoryForm } from "./inventory-form";

describe("InventoryForm", () => {
  it("ruft onSubmit mit den eingegebenen Werten", async () => {
    const onSubmit = vi.fn();
    render(<InventoryForm onSubmit={onSubmit} />);

    await userEvent.type(screen.getByTestId("inventory-input-name"), "react");
    await userEvent.type(screen.getByTestId("inventory-input-version"), "18.2.0");
    await userEvent.selectOptions(screen.getByTestId("inventory-select-category"), "library");
    await userEvent.click(screen.getByTestId("inventory-btn-submit"));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit.mock.calls[0]?.[0]).toMatchObject({
      name: "react",
      version: "18.2.0",
      category: "library",
    });
  });

  it("zeigt einen Fehler und sendet nicht bei leerem Formular", async () => {
    const onSubmit = vi.fn();
    render(<InventoryForm onSubmit={onSubmit} />);

    await userEvent.click(screen.getByTestId("inventory-btn-submit"));

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByTestId("inventory-error-name")).toBeInTheDocument();
  });
});
