import { describe, expect, it } from "vitest";

import { severityCountsOf } from "./stats";

describe("severityCountsOf", () => {
  it("liefert alle vier Stufen in fester Reihenfolge mit den Anzahlen", () => {
    const result = severityCountsOf({ niedrig: 9, mittel: 0, hoch: 10, kritisch: 3 });

    expect(result.map((entry) => entry.level)).toEqual(["kritisch", "hoch", "mittel", "niedrig"]);
    expect(result.map((entry) => entry.count)).toEqual([3, 10, 0, 9]);
  });
});
