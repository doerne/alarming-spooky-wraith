import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { MultiToggleFilter } from "./multi-toggle-filter";

const OPTIONS = [
  { value: "a", label: "Alpha" },
  { value: "b", label: "Beta" },
];

describe("MultiToggleFilter", () => {
  it("fügt einen Wert zur Auswahl hinzu", async () => {
    const onChange = vi.fn();
    render(
      <MultiToggleFilter
        label="Test"
        options={OPTIONS}
        selected={["a"]}
        onChange={onChange}
        testIdPrefix="shared-select-test"
      />,
    );

    await userEvent.click(screen.getByTestId("shared-select-test-b"));

    expect(onChange).toHaveBeenCalledWith(["a", "b"]);
  });

  it("entfernt einen gewählten Wert", async () => {
    const onChange = vi.fn();
    render(
      <MultiToggleFilter
        label="Test"
        options={OPTIONS}
        selected={["a", "b"]}
        onChange={onChange}
        testIdPrefix="shared-select-test"
      />,
    );

    await userEvent.click(screen.getByTestId("shared-select-test-a"));

    expect(onChange).toHaveBeenCalledWith(["b"]);
  });
});
