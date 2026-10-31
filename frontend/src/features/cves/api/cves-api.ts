import { request } from "@/shared/api/http-client";

import { type Finding, findingsPageSchema } from "../model/types";

export async function fetchFindings(): Promise<Finding[]> {
  const page = findingsPageSchema.parse(await request("/api/cves"));
  return page.items;
}

export async function runIngest(): Promise<void> {
  await request("/api/ingest/run", { method: "POST" });
}
