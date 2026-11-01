import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ColumnFilter, ColumnSearch } from "./column-filter";

const OPTIONS = [
  { value: "1", label: "Shop" },
  { value: "2", label: "Blog" },
  { value: "3", label: "Shopware" },
];

function renderFilter(selected: string[] = [], searchable = false) {
  const onChange = vi.fn();
  render(
    <ColumnFilter
      label="Anwendung"
      options={OPTIONS}
      selected={selected}
      onChange={onChange}
      searchable={searchable}
      testIdPrefix="shared-filter-test-app"
    />,
  );
  return onChange;
}

describe("ColumnFilter", () => {
  it("öffnet die Liste und wählt einen Wert", async () => {
    const onChange = renderFilter(["1"]);

    await userEvent.click(screen.getByTestId("shared-filter-test-app"));
    await userEvent.click(screen.getByTestId("shared-filter-test-app-option-2"));

    expect(onChange).toHaveBeenCalledWith(["1", "2"]);
  });

  it("wählt einen Wert ab", async () => {
    const onChange = renderFilter(["1", "2"]);

    await userEvent.click(screen.getByTestId("shared-filter-test-app"));
    await userEvent.click(screen.getByTestId("shared-filter-test-app-option-1"));

    expect(onChange).toHaveBeenCalledWith(["2"]);
  });

  it("zeigt die Anzahl gewählter Werte im Kopf", () => {
    renderFilter(["1", "3"]);

    expect(screen.getByTestId("shared-filter-test-app")).toHaveTextContent("2");
  });

  it("durchsucht die Optionen und meldet fehlende Treffer", async () => {
    renderFilter([], true);

    await userEvent.click(screen.getByTestId("shared-filter-test-app"));
    await userEvent.type(screen.getByTestId("shared-filter-test-app-search"), "shop");

    expect(screen.getByTestId("shared-filter-test-app-option-1")).toBeInTheDocument();
    expect(screen.getByTestId("shared-filter-test-app-option-3")).toBeInTheDocument();
    expect(screen.queryByTestId("shared-filter-test-app-option-2")).not.toBeInTheDocument();

    await userEvent.clear(screen.getByTestId("shared-filter-test-app-search"));
    await userEvent.type(screen.getByTestId("shared-filter-test-app-search"), "xyz");
    expect(screen.getByTestId("shared-filter-test-app-empty")).toHaveTextContent("Keine Treffer");
  });

  it("löscht die Auswahl", async () => {
    const onChange = renderFilter(["1"]);

    await userEvent.click(screen.getByTestId("shared-filter-test-app"));
    await userEvent.click(screen.getByTestId("shared-filter-test-app-clear"));

    expect(onChange).toHaveBeenCalledWith([]);
  });

  it("öffnet per Tastatur und schließt mit Esc", async () => {
    renderFilter();

    screen.getByTestId("shared-filter-test-app").focus();
    await userEvent.keyboard("{Enter}");
    expect(screen.getByTestId("shared-filter-test-app-option-1")).toBeInTheDocument();

    await userEvent.keyboard("{Escape}");
    expect(screen.queryByTestId("shared-filter-test-app-option-1")).not.toBeInTheDocument();
  });
});

describe("ColumnSearch", () => {
  it("meldet die Eingabe und hat ein Label", async () => {
    const onChange = vi.fn();
    render(
      <ColumnSearch label="Komponente" value="" onChange={onChange} testId="shared-input-test-comp" />,
    );

    await userEvent.type(screen.getByTestId("shared-input-test-comp"), "d");

    expect(onChange).toHaveBeenCalledWith("d");
    expect(screen.getByLabelText("Komponente filtern")).toBeInTheDocument();
  });
});
