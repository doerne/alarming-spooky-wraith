import { request } from "@/shared/api/http-client";

import type { CveFilters } from "../model/cve-filters";
import type { ApplicationInput, ComponentInput } from "../model/schema";
import type { Application, ApplicationDetail, ApplicationFinding } from "../model/types";

export type { Application, ApplicationDetail, Component } from "../model/types";

export interface ApplicationFindingsPage {
  items: ApplicationFinding[];
  total: number;
  unfilteredTotal: number;
}

export async function listApplications(): Promise<Application[]> {
  return request<Application[]>("/api/applications");
}

export async function getApplication(applicationId: number): Promise<ApplicationDetail> {
  return request<ApplicationDetail>(`/api/applications/${applicationId}`);
}

export function applicationFindingsPath(applicationId: number, filters: CveFilters): string {
  const params = new URLSearchParams({ application_id: String(applicationId) });
  for (const severity of filters.severities) params.append("severity", severity);
  for (const status of filters.statuses) params.append("status", status);
  for (const ecosystem of filters.ecosystems) params.append("ecosystem", ecosystem);
  for (const id of filters.advisoryIds) params.append("advisory_id", id);
  for (const name of filters.componentNames) params.append("component_name", name);
  return `/api/cves?${params.toString()}`;
}

export async function listApplicationFindings(
  applicationId: number,
  filters: CveFilters,
): Promise<ApplicationFindingsPage> {
  return request<ApplicationFindingsPage>(applicationFindingsPath(applicationId, filters));
}

export async function createApplication(input: ApplicationInput): Promise<Application> {
  return request<Application>("/api/applications", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function addComponent(applicationId: number, input: ComponentInput): Promise<void> {
  await request(`/api/applications/${applicationId}/components`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function updateComponent(
  applicationId: number,
  componentId: number,
  input: ComponentInput,
): Promise<void> {
  await request(`/api/applications/${applicationId}/components/${componentId}`, {
    method: "PUT",
    body: JSON.stringify(input),
  });
}
