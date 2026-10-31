import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Application } from "../model/types";
import { ApplicationList } from "./application-list";

const apps: Application[] = [
  { id: 1, name: "Shop", description: "" },
  { id: 2, name: "Blog", description: "" },
];

describe("ApplicationList", () => {
  it("zeigt alle Anwendungen und meldet die Auswahl", async () => {
    const onSelect = vi.fn();
    render(<ApplicationList applications={apps} onSelect={onSelect} />);

    expect(screen.getByTestId("inventory-item-app-1")).toHaveTextContent("Shop");

    await userEvent.click(screen.getByTestId("inventory-item-app-2"));

    expect(onSelect).toHaveBeenCalledWith(2);
  });

  it("zeigt einen Hinweis, wenn noch keine Anwendung existiert", () => {
    render(<ApplicationList applications={[]} onSelect={vi.fn()} />);

    expect(screen.getByTestId("inventory-text-empty")).toBeInTheDocument();
  });
});
