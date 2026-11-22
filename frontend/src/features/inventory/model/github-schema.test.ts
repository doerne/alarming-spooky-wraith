import { describe, expect, it } from "vitest";

import { isValidRepository } from "./github-schema";

describe("isValidRepository", () => {
  it.each([
    ["acme/shop", true],
    ["acme/shop.web-2_x", true],
    ["acme/..", false],
    ["acme/.", false],
    ["../shop", false],
    ["acme", false],
    ["acme/shop\nx", false],
  ])("%s → %s", (value, valid) => {
    expect(isValidRepository(value)).toBe(valid);
  });
});
