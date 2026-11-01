import { request } from "@/shared/api/http-client";

import {
  type CveDetail,
  type Finding,
  type FindingsPage,
  cveDetailSchema,
  type IngestState,
  findingsPageSchema,
  ingestStateSchema,
} from "../model/types";
import type { FindingFilters } from "../model/filters";

export async function fetchFindings(): Promise<Finding[]> {
  const page = findingsPageSchema.parse(await request("/api/cves"));
  return page.items;
}

/** Query-String für die API; Mehrfachwerte als wiederholte Parameter. */
export function buildFindingsQuery(filters: FindingFilters): string {
  const params = new URLSearchParams();
  for (const severity of filters.severities) params.append("severity", severity);
  for (const status of filters.statuses) params.append("status", status);
  for (const ecosystem of filters.ecosystems) params.append("ecosystem", ecosystem);
  for (const id of filters.applicationIds) params.append("application", String(id));
  for (const id of filters.advisoryIds) params.append("advisory_id", id);
  for (const name of filters.componentNames) params.append("component_name", name);
  const text = params.toString();
  return text ? `?${text}` : "";
}

export async function fetchFilteredFindings(filters: FindingFilters): Promise<FindingsPage> {
  return findingsPageSchema.parse(await request(`/api/cves${buildFindingsQuery(filters)}`));
}

export async function startIngest(): Promise<IngestState> {
  return ingestStateSchema.parse(await request("/api/ingest/run", { method: "POST" }));
}

export async function fetchIngestStatus(): Promise<IngestState> {
  return ingestStateSchema.parse(await request("/api/ingest/status"));
}

export async function fetchCveDetail(advisoryId: string): Promise<CveDetail> {
  return cveDetailSchema.parse(await request(`/api/cves/${encodeURIComponent(advisoryId)}`));
}
