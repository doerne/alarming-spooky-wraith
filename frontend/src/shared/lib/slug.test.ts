import { describe, expect, it } from "vitest";

import { slug } from "./slug";

describe("slug", () => {
  it("macht kebab-case aus Punkten, Großbuchstaben und Unterstrichen", () => {
    expect(slug("crates.io")).toBe("crates-io");
    expect(slug("PyPI")).toBe("pypi");
    expect(slug("false_positive")).toBe("false-positive");
    expect(slug("..x..")).toBe("x");
  });
});
