import { request } from "@/shared/api/http-client";

import { type Source, sourceSchema, sourcesSchema } from "../model/types";

function sourcePath(key: string): string {
  return `/api/sources/${encodeURIComponent(key)}`;
}

export async function fetchSources(): Promise<Source[]> {
  return sourcesSchema.parse(await request("/api/sources"));
}

export async function setSourceEnabled(input: { key: string; enabled: boolean }): Promise<Source> {
  const body = JSON.stringify({ enabled: input.enabled });
  return sourceSchema.parse(await request(sourcePath(input.key), { method: "PATCH", body }));
}

export async function setSourceApiKey(input: { key: string; apiKey: string }): Promise<Source> {
  const body = JSON.stringify({ apiKey: input.apiKey });
  const path = `${sourcePath(input.key)}/api-key`;
  return sourceSchema.parse(await request(path, { method: "PUT", body }));
}

export async function removeSourceApiKey(key: string): Promise<Source> {
  return sourceSchema.parse(await request(`${sourcePath(key)}/api-key`, { method: "DELETE" }));
}
