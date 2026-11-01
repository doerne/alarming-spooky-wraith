import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SearchInput } from "./search-input";

describe("SearchInput", () => {
  it("meldet die Eingabe und hat ein zugängliches Label", async () => {
    const onChange = vi.fn();
    render(
      <SearchInput
        value=""
        onChange={onChange}
        placeholder="Suchen"
        testId="shared-input-test-search"
      />,
    );

    await userEvent.type(screen.getByTestId("shared-input-test-search"), "x");

    expect(onChange).toHaveBeenCalledWith("x");
    expect(screen.getByLabelText("Suchen")).toBeInTheDocument();
  });
});
