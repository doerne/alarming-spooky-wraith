import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SourceAlerts } from "./source-alerts";

describe("SourceAlerts", () => {
  it("zeigt Fehler beim Umschalten", () => {
    render(<SourceAlerts loadError={null} toggleError={new Error("HTTP 500")} />);

    expect(screen.getByTestId("sources-error-toggle")).toHaveTextContent("HTTP 500");
    expect(screen.queryByTestId("sources-error-load")).not.toBeInTheDocument();
  });
});
