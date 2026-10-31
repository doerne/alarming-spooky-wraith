import { request } from "@/shared/api/http-client";

import type { ApplicationInput, ComponentInput } from "../model/schema";
import type { Application, ApplicationDetail, ApplicationFinding } from "../model/types";

export type { Application, ApplicationDetail, Component } from "../model/types";

interface FindingsPage {
  items: ApplicationFinding[];
  total: number;
}

export async function listApplications(): Promise<Application[]> {
  return request<Application[]>("/api/applications");
}

export async function getApplication(applicationId: number): Promise<ApplicationDetail> {
  return request<ApplicationDetail>(`/api/applications/${applicationId}`);
}

export async function listApplicationFindings(
  applicationId: number,
): Promise<ApplicationFinding[]> {
  const page = await request<FindingsPage>(`/api/cves?application_id=${applicationId}`);
  return page.items;
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
