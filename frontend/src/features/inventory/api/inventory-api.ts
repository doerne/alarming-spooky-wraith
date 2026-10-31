import { request } from "@/shared/api/http-client";

import type { ApplicationInput, ComponentInput } from "../model/schema";

export interface Application {
  id: number;
  name: string;
  description: string;
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
