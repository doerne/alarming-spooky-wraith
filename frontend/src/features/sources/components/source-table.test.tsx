import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SourceTable } from "./source-table";
import { makeSource } from "./test-data";

const snyk = makeSource({
  key: "snyk",
  name: "Snyk",
  apiKeyRequirement: "required",
  status: "missing_key",
});

function renderTable(sources = [makeSource(), snyk]) {
  const onToggle = vi.fn();
  const onEditApiKey = vi.fn();
  render(<SourceTable sources={sources} onToggle={onToggle} onEditApiKey={onEditApiKey} />);
  return { onToggle, onEditApiKey };
}

describe("SourceTable", () => {
  it("zeigt Name und Status je Quelle", () => {
    renderTable();

    expect(screen.getByTestId("sources-item-osv")).toHaveTextContent("OSV.dev");
    expect(screen.getByTestId("sources-text-status-osv")).toHaveTextContent("Bereit");
    expect(screen.getByTestId("sources-text-status-snyk")).toHaveTextContent("Key fehlt");
    expect(screen.getByTestId("sources-link-homepage-osv")).toHaveAttribute(
      "href",
      "https://osv.dev",
    );
  });

  it("meldet das Umschalten einer Quelle", async () => {
    const { onToggle } = renderTable();

    await userEvent.click(screen.getByTestId("sources-checkbox-enabled-osv"));

    expect(onToggle).toHaveBeenCalledWith("osv", false);
  });

  it("zeigt die Key-Aktion nur bei Quellen mit Key", async () => {
    const { onEditApiKey } = renderTable();

    expect(screen.queryByTestId("sources-btn-api-key-osv")).not.toBeInTheDocument();
    await userEvent.click(screen.getByTestId("sources-btn-api-key-snyk"));

    expect(onEditApiKey).toHaveBeenCalledWith("snyk");
    expect(screen.getByTestId("sources-btn-api-key-snyk")).toHaveTextContent("Key hinterlegen");
  });

  it("nennt einen vorhandenen Key 'Key ändern'", () => {
    renderTable([makeSource({ ...snyk, hasApiKey: true, status: "ready" })]);

    expect(screen.getByTestId("sources-btn-api-key-snyk")).toHaveTextContent("Key ändern");
  });

  it("zeigt Fehler und Funde des letzten Laufs", () => {
    renderTable([
      makeSource({ lastStatus: "error", lastMessage: "Rate-Limit erreicht" }),
      makeSource({ key: "ghsa", name: "GHSA", lastStatus: "ok", lastFindings: 7 }),
    ]);

    expect(screen.getByTestId("sources-text-last-run-osv")).toHaveTextContent(
      "Rate-Limit erreicht",
    );
    expect(screen.getByTestId("sources-text-last-run-ghsa")).toHaveTextContent("7 Funde");
  });
});
