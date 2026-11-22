import { describe, expect, it } from "vitest";

import { githubSyncHint } from "./github-hint";

describe("githubSyncHint", () => {
  it("nennt die fehlende Konfiguration zuerst", () => {
    expect(githubSyncHint({ repository: null, configured: false, running: true })).toMatch(
      /nicht konfiguriert/,
    );
  });

  it("verlangt ein Repository", () => {
    expect(githubSyncHint({ repository: null, configured: true, running: false })).toMatch(
      /Repository/,
    );
  });

  it("meldet einen laufenden Abgleich", () => {
    expect(githubSyncHint({ repository: "acme/shop", configured: true, running: true })).toMatch(
      /läuft/,
    );
  });

  it("ist null, wenn alles bereit ist", () => {
    expect(
      githubSyncHint({ repository: "acme/shop", configured: true, running: false }),
    ).toBeNull();
  });
});
