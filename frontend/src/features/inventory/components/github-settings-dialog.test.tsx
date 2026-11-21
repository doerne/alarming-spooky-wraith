import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { GithubSettingsDialog } from "./github-settings-dialog";

function renderDialog(onSave = vi.fn(), error: string | null = null) {
  render(
    <GithubSettingsDialog
      repository={null}
      autoIssueMinLevel={null}
      isSaving={false}
      error={error}
      onSave={onSave}
      onCancel={vi.fn()}
    />,
  );
  return onSave;
}

describe("GithubSettingsDialog", () => {
  it("speichert Repository und Automatik-Stufe", async () => {
    const onSave = renderDialog();

    await userEvent.type(screen.getByTestId("inventory-input-github-repository"), "acme/shop");
    await userEvent.selectOptions(screen.getByTestId("inventory-select-github-auto-level"), "hoch");
    await userEvent.click(screen.getByRole("button", { name: "Speichern" }));

    await waitFor(() =>
      expect(onSave).toHaveBeenCalledWith({ repository: "acme/shop", autoIssueMinLevel: "hoch" }),
    );
  });

  it("weist ein ungültiges Repository zurück, ohne zu speichern", async () => {
    const onSave = renderDialog();

    await userEvent.type(screen.getByTestId("inventory-input-github-repository"), "acme/..");
    await userEvent.click(screen.getByRole("button", { name: "Speichern" }));

    expect(await screen.findByTestId("inventory-error-github-repository")).toHaveTextContent(
      "owner/repo",
    );
    expect(onSave).not.toHaveBeenCalled();
  });

  it("zeigt einen Speicherfehler der API", () => {
    renderDialog(vi.fn(), "Repository als owner/repo angeben");

    expect(screen.getByTestId("inventory-error-github-save")).toHaveTextContent("owner/repo");
  });
});
