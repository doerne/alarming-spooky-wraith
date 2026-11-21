import { request } from "@/shared/api/http-client";

import type {
  SbomSummary,
  SbomUploadBody,
  SbomUploadResult,
  SbomVersionDetail,
  SbomVersionSummary,
} from "../model/sbom-types";

function sbomsPath(applicationId: number): string {
  return `/api/applications/${applicationId}/sboms`;
}

export async function listSboms(applicationId: number): Promise<SbomSummary[]> {
  return request<SbomSummary[]>(sbomsPath(applicationId));
}

export async function uploadSbomVersion(
  applicationId: number,
  body: SbomUploadBody,
): Promise<SbomUploadResult> {
  return request<SbomUploadResult>(`${sbomsPath(applicationId)}/versions`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function listSbomVersions(
  applicationId: number,
  sbomId: number,
): Promise<SbomVersionSummary[]> {
  return request<SbomVersionSummary[]>(`${sbomsPath(applicationId)}/${sbomId}/versions`);
}

export async function getSbomVersion(
  applicationId: number,
  sbomId: number,
  versionId: number,
): Promise<SbomVersionDetail> {
  return request<SbomVersionDetail>(
    `${sbomsPath(applicationId)}/${sbomId}/versions/${versionId}`,
  );
}

export async function deleteSbom(applicationId: number, sbomId: number): Promise<void> {
  await request(`${sbomsPath(applicationId)}/${sbomId}`, { method: "DELETE" });
}
