import { request } from "@/shared/api/http-client";

import {
  type Finding,
  type IngestState,
  findingsPageSchema,
  ingestStateSchema,
} from "../model/types";

export async function fetchFindings(): Promise<Finding[]> {
  const page = findingsPageSchema.parse(await request("/api/cves"));
  return page.items;
}

export async function startIngest(): Promise<IngestState> {
  return ingestStateSchema.parse(await request("/api/ingest/run", { method: "POST" }));
}

export async function fetchIngestStatus(): Promise<IngestState> {
  return ingestStateSchema.parse(await request("/api/ingest/status"));
}
