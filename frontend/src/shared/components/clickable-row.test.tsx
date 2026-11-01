import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Table, TableBody, TableCell } from "@/shared/ui/table";

import { ClickableRow } from "./clickable-row";

function renderRow(onActivate = vi.fn()) {
  render(
    <Table data-testid="shared-list-test-rows">
      <TableBody>
        <ClickableRow label="Details zu X" testId="shared-item-test-row" onActivate={onActivate}>
          <TableCell>Inhalt</TableCell>
        </ClickableRow>
      </TableBody>
    </Table>,
  );
  return onActivate;
}

describe("ClickableRow", () => {
  it("löst per Klick aus", async () => {
    const onActivate = renderRow();

    await userEvent.click(screen.getByTestId("shared-item-test-row"));

    expect(onActivate).toHaveBeenCalledTimes(1);
  });

  it.each(["{Enter}", " "])("löst per Taste %s aus", async (key) => {
    const onActivate = renderRow();

    screen.getByTestId("shared-item-test-row").focus();
    await userEvent.keyboard(key);

    expect(onActivate).toHaveBeenCalledTimes(1);
  });

  it("ignoriert andere Tasten", async () => {
    const onActivate = renderRow();

    screen.getByTestId("shared-item-test-row").focus();
    await userEvent.keyboard("a");

    expect(onActivate).not.toHaveBeenCalled();
  });
});
