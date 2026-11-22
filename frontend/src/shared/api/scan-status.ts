import { z } from "zod";

import { request } from "./http-client";

export const scanRunSchema = z.object({
  trigger: z.enum(["manual", "schedule", "catch_up"]),
  outcome: z.enum(["ok", "incomplete", "failed"]).nullable(),
  startedAt: z.string(),
  finishedAt: z.string().nullable(),
  componentsScanned: z.number().nullable(),
  findingsFound: z.number().nullable(),
  sourcesWithErrors: z.number(),
  message: z.string(),
});
export type ScanRun = z.infer<typeof scanRunSchema>;

export const scanStepStateSchema = z.enum(["pending", "running", "done", "skipped", "failed"]);
export type ScanStepState = z.infer<typeof scanStepStateSchema>;

export const scanStepSchema = z.object({
  key: z.string(),
  label: z.string(),
  state: scanStepStateSchema,
  detail: z.string(),
});
export type ScanStep = z.infer<typeof scanStepSchema>;

/** Schlussschritte nach den Quellen, wie in backend/app/application/scan_progress.py. */
export const FINAL_SCAN_STEP_KEYS: ReadonlySet<string> = new Set(["persist", "github-sync"]);

export const scanStatusSchema = z.object({
  running: z.boolean(),
  startedAt: z.string().nullable(),
  finishedAt: z.string().nullable(),
  componentsScanned: z.number().nullable(),
  findingsFound: z.number().nullable(),
  error: z.string().nullable(),
  lastRun: scanRunSchema.nullable(),
  lastUsableRun: scanRunSchema.nullable(),
  steps: z.array(scanStepSchema),
});
export type ScanStatus = z.infer<typeof scanStatusSchema>;

/** Gemeinsamer Cache-Schlüssel, damit alle Features denselben Scan-Zustand teilen. */
export const SCAN_STATUS_QUERY_KEY = ["ingest-status"] as const;

export async function fetchScanStatus(): Promise<ScanStatus> {
  return scanStatusSchema.parse(await request("/api/ingest/status"));
}

export async function startScan(): Promise<ScanStatus> {
  return scanStatusSchema.parse(await request("/api/ingest/run", { method: "POST" }));
}
