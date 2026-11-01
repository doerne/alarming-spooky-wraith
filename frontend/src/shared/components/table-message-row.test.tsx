import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Table, TableBody } from "@/shared/ui/table";

import { FilterSummaryBar } from "./filter-summary-bar";
import { NoResultsRow, TableMessageRow } from "./table-message-row";

function inTable(node: React.ReactNode) {
  return render(
    <Table data-testid="shared-list-test-table">
      <TableBody>{node}</TableBody>
    </Table>,
  );
}

describe("NoResultsRow", () => {
  it("zeigt Hinweis und setzt zurück", async () => {
    const onReset = vi.fn();
    inTable(<NoResultsRow colSpan={3} feature="shared" onReset={onReset} />);

    expect(screen.getByTestId("shared-text-no-results")).toHaveTextContent(
      "Keine Funde für diese Filter",
    );
    await userEvent.click(screen.getByTestId("shared-btn-reset-no-results"));
    expect(onReset).toHaveBeenCalled();
  });
});

describe("TableMessageRow", () => {
  it("zeigt eine Meldung über alle Spalten", () => {
    inTable(
      <TableMessageRow colSpan={3} testId="shared-text-test-message">
        Noch keine Funde
      </TableMessageRow>,
    );

    expect(screen.getByTestId("shared-text-test-message").closest("td")).toHaveAttribute(
      "colspan",
      "3",
    );
  });
});

describe("FilterSummaryBar", () => {
  it("zeigt N von M und sperrt Zurücksetzen ohne aktive Filter", async () => {
    const onReset = vi.fn();
    const { rerender } = render(
      <FilterSummaryBar shown={3} total={5} active feature="shared" onReset={onReset} />,
    );

    expect(screen.getByTestId("shared-text-filter-summary")).toHaveTextContent("3 von 5 Funden");
    await userEvent.click(screen.getByTestId("shared-btn-reset-filters"));
    expect(onReset).toHaveBeenCalled();

    rerender(
      <FilterSummaryBar shown={5} total={5} active={false} feature="shared" onReset={onReset} />,
    );
    expect(screen.getByTestId("shared-btn-reset-filters")).toBeDisabled();
  });
});
