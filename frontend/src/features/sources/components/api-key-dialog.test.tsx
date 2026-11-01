import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiKeyDialog } from "./api-key-dialog";
import { makeSource } from "./test-data";

const snyk = makeSource({
  key: "snyk",
  name: "Snyk",
  apiKeyRequirement: "required",
  apiKeyHint: "Format <org-id>:<token>",
});

function renderDialog(source = snyk) {
  const props = { onSave: vi.fn(), onRemove: vi.fn(), onClose: vi.fn() };
  render(<ApiKeyDialog source={source} {...props} />);
  return props;
}

describe("ApiKeyDialog", () => {
  it("verlangt einen Key und speichert nicht bei leerem Feld", async () => {
    const { onSave } = renderDialog();

    await userEvent.type(screen.getByTestId("sources-input-api-key"), "   ");
    await userEvent.click(screen.getByTestId("sources-btn-save-api-key"));

    expect(screen.getByTestId("sources-error-api-key")).toHaveTextContent("erforderlich");
    expect(onSave).not.toHaveBeenCalled();
  });

  it("speichert den eingegebenen Key", async () => {
    const { onSave } = renderDialog();

    await userEvent.type(screen.getByTestId("sources-input-api-key"), "org:abc");
    await userEvent.click(screen.getByTestId("sources-btn-save-api-key"));

    expect(onSave).toHaveBeenCalledWith("org:abc");
  });

  it("verbirgt die Eingabe und zeigt den Format-Hinweis", () => {
    renderDialog();

    expect(screen.getByTestId("sources-input-api-key")).toHaveAttribute("type", "password");
    expect(screen.getByTestId("sources-dialog-api-key")).toHaveTextContent(
      "Format <org-id>:<token>",
    );
  });

  it("bietet Entfernen nur bei hinterlegtem Key an", () => {
    renderDialog();

    expect(screen.queryByTestId("sources-btn-remove-api-key")).not.toBeInTheDocument();
  });

  it("entfernt einen hinterlegten Key", async () => {
    const { onRemove } = renderDialog({ ...snyk, hasApiKey: true });

    await userEvent.click(screen.getByTestId("sources-btn-remove-api-key"));

    expect(onRemove).toHaveBeenCalled();
  });

  it("rendert nichts ohne Quelle", () => {
    render(<ApiKeyDialog source={null} onSave={vi.fn()} onRemove={vi.fn()} onClose={vi.fn()} />);

    expect(screen.queryByTestId("sources-dialog-api-key")).not.toBeInTheDocument();
  });
});

describe("ApiKeyDialog mit Fehler", () => {
  it("zeigt einen Fehler beim Speichern", () => {
    render(
      <ApiKeyDialog
        source={snyk}
        error="API-Key darf nicht leer sein"
        onSave={vi.fn()}
        onRemove={vi.fn()}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByTestId("sources-error-save")).toHaveTextContent(
      "API-Key darf nicht leer sein",
    );
  });
});
