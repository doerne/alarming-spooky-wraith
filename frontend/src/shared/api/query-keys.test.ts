import { describe, expect, it } from "vitest";

import { queryKeys } from "./query-keys";

describe("queryKeys", () => {
  it("liefert unveränderte Schlüssel", () => {
    expect(queryKeys.findings).toEqual(["findings"]);
    expect(queryKeys.applicationFindings(3)).toEqual(["application-findings", 3]);
    expect(queryKeys.application(3)).toEqual(["application", 3]);
  });
});
