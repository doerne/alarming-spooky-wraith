import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { GithubCreateDialog } from "./github-create-dialog";

describe("GithubCreateDialog", () => {
  it("schlägt die Stufe „hoch“ vor und reicht die Wahl weiter", async () => {
    const onConfirm = vi.fn();
    render(<GithubCreateDialog isStarting={false} onConfirm={onConfirm} onCancel={vi.fn()} />);

    const select = screen.getByTestId("inventory-select-github-min-level");
    expect(select).toHaveValue("hoch");
    await userEvent.selectOptions(select, "kritisch");
    await userEvent.click(screen.getByRole("button", { name: "Anlegen starten" }));

    await waitFor(() => expect(onConfirm).toHaveBeenCalledWith({ minLevel: "kritisch" }));
  });

  it("bricht ohne Anlage ab", async () => {
    const onCancel = vi.fn();
    render(<GithubCreateDialog isStarting={false} onConfirm={vi.fn()} onCancel={onCancel} />);

    await userEvent.click(screen.getByTestId("inventory-btn-github-cancel"));

    expect(onCancel).toHaveBeenCalledOnce();
  });
});
