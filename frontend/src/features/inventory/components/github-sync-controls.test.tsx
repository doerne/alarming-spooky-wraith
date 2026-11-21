import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { GithubSyncControls } from "./github-sync-controls";

const base = {
  hint: null,
  lastSyncedAt: null,
  lastSyncMessage: "",
  error: null,
  onOpenCreate: vi.fn(),
  onSync: vi.fn(),
};

describe("GithubSyncControls", () => {
  it("startet den Abgleich und öffnet den Anlege-Dialog über Buttons", async () => {
    const onSync = vi.fn();
    const onOpenCreate = vi.fn();
    render(<GithubSyncControls {...base} onSync={onSync} onOpenCreate={onOpenCreate} />);

    await userEvent.click(screen.getByTestId("inventory-btn-github-sync"));
    await userEvent.click(screen.getByTestId("inventory-btn-github-create"));

    expect(onSync).toHaveBeenCalledOnce();
    expect(onOpenCreate).toHaveBeenCalledOnce();
  });

  it("deaktiviert beide Buttons und zeigt den Grund", () => {
    render(<GithubSyncControls {...base} hint="Hinterlege zuerst ein Repository." />);

    expect(screen.getByTestId("inventory-btn-github-sync")).toBeDisabled();
    expect(screen.getByTestId("inventory-btn-github-create")).toBeDisabled();
    expect(screen.getByTestId("inventory-text-github-hint")).toHaveTextContent("Repository");
  });

  it("zeigt Zeitpunkt und Meldung des letzten Abgleichs", () => {
    render(
      <GithubSyncControls
        {...base}
        lastSyncedAt="2026-11-21T12:00:00Z"
        lastSyncMessage="2 angelegt"
      />,
    );

    expect(screen.getByTestId("inventory-text-github-sync-status")).toHaveTextContent(
      "Letzter Abgleich:",
    );
    expect(screen.getByTestId("inventory-text-github-sync-status")).toHaveTextContent("2 angelegt");
  });

  it("zeigt einen Startfehler als Hinweis", () => {
    render(<GithubSyncControls {...base} error="Ein Scan oder Abgleich läuft bereits" />);

    expect(screen.getByTestId("inventory-error-github-sync")).toHaveTextContent("läuft bereits");
  });
});
