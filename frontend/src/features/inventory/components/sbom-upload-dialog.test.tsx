import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SbomUploadDialog } from "./sbom-upload-dialog";

const DOCUMENT = {
  bomFormat: "CycloneDX",
  metadata: { component: { name: "backend", version: "1.4.0" } },
  components: [],
};

function sbomFile(content: unknown = DOCUMENT, name = "backend.cdx.json"): File {
  const text = typeof content === "string" ? content : JSON.stringify(content);
  return new File([text], name, { type: "application/json" });
}

function renderDialog(props: { fixedName?: string | null; error?: string | null } = {}) {
  const onSubmit = vi.fn();
  render(
    <SbomUploadDialog
      open
      fixedName={props.fixedName ?? null}
      isSubmitting={false}
      error={props.error ?? null}
      onSubmit={onSubmit}
      onOpenChange={vi.fn()}
    />,
  );
  return onSubmit;
}

describe("SbomUploadDialog", () => {
  it("belegt Name und Version aus der Datei vor und sendet sie", async () => {
    const onSubmit = renderDialog();
    await userEvent.upload(screen.getByTestId("inventory-input-sbom-file"), sbomFile());

    await waitFor(() =>
      expect(screen.getByTestId("inventory-input-sbom-name")).toHaveValue("backend"),
    );
    expect(screen.getByTestId("inventory-input-sbom-label")).toHaveValue("1.4.0");
    await userEvent.click(screen.getByTestId("inventory-btn-sbom-submit"));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit).toHaveBeenCalledWith({
      name: "backend",
      label: "1.4.0",
      document: DOCUMENT,
    });
  });

  it("zeigt einen Fehler bei ungültiger Datei und sendet nichts", async () => {
    const onSubmit = renderDialog();
    await userEvent.upload(
      screen.getByTestId("inventory-input-sbom-file"),
      sbomFile({ spdxVersion: "SPDX-2.3" }),
    );

    expect(await screen.findByTestId("inventory-error-sbom-file")).toHaveTextContent(
      "Die Datei ist keine CycloneDX-SBOM.",
    );
    await userEvent.click(screen.getByTestId("inventory-btn-sbom-submit"));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("verlangt eine Datei", async () => {
    const onSubmit = renderDialog();
    await userEvent.type(screen.getByTestId("inventory-input-sbom-name"), "backend");
    await userEvent.click(screen.getByTestId("inventory-btn-sbom-submit"));
    expect(await screen.findByTestId("inventory-error-sbom-file")).toHaveTextContent(
      "Bitte eine SBOM-Datei wählen.",
    );
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("sperrt den Namen bei neuer Version", async () => {
    renderDialog({ fixedName: "backend-image" });
    const name = screen.getByTestId("inventory-input-sbom-name");
    expect(name).toHaveValue("backend-image");
    expect(name).toHaveAttribute("readonly");
    await userEvent.upload(screen.getByTestId("inventory-input-sbom-file"), sbomFile());
    await waitFor(() =>
      expect(screen.getByTestId("inventory-input-sbom-label")).toHaveValue("1.4.0"),
    );
    expect(name).toHaveValue("backend-image");
  });

  it("zeigt Serverfehler", () => {
    renderDialog({ error: "Diese SBOM ist bereits die aktuelle Version" });
    expect(screen.getByTestId("inventory-error-sbom-upload")).toHaveTextContent("bereits");
  });
});
