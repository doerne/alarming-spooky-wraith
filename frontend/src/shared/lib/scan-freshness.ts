import type { ScanRun, ScanStatus } from "@/shared/api/scan-status";

/** 24 h plus Puffer, damit der morgendliche Lauf nicht jedes Mal eine Warnung auslöst. */
export const STALE_AFTER_MS = 26 * 60 * 60 * 1000;

const SEPARATOR = " · ";
const NOT_SCANNED = "Noch nicht gescannt – Änderungen seit dem letzten Scan";
const NO_SCAN = "Noch kein vollständiger Scan";

export interface ScanFreshnessInput {
  status: ScanStatus;
  now: Date;
  inventoryChangedAt?: string | null;
}

export interface ScanFreshnessView {
  text: string;
  warning: boolean;
}

const timeFormat = new Intl.DateTimeFormat("de-DE", { hour: "2-digit", minute: "2-digit" });
const dayFormat = new Intl.DateTimeFormat("de-DE", { day: "2-digit", month: "2-digit" });

function isSameDay(left: Date, right: Date): boolean {
  return left.toDateString() === right.toDateString();
}

function formatMoment(moment: Date, now: Date): string {
  const time = timeFormat.format(moment);
  return isSameDay(moment, now) ? `heute ${time}` : `${dayFormat.format(moment)} ${time}`;
}

function sourcesText(count: number): string {
  return count === 1 ? "1 Quelle mit Fehlern" : `${count} Quellen mit Fehlern`;
}

function failedAfter(lastRun: ScanRun | null, usable: ScanRun): boolean {
  return lastRun?.outcome === "failed" && new Date(lastRun.startedAt) > new Date(usable.startedAt);
}

function warningsFor(usable: ScanRun, lastRun: ScanRun | null, now: Date): string[] {
  const finished = new Date(usable.finishedAt ?? usable.startedAt);
  const warnings: string[] = [];
  if (now.getTime() - finished.getTime() > STALE_AFTER_MS) warnings.push("älter als ein Tag");
  if (usable.outcome === "incomplete") warnings.push(sourcesText(usable.sourcesWithErrors));
  if (failedAfter(lastRun, usable)) warnings.push("letzter Scan fehlgeschlagen");
  return warnings;
}

function standFor(usable: ScanRun, lastRun: ScanRun | null, now: Date): ScanFreshnessView {
  const finished = new Date(usable.finishedAt ?? usable.startedAt);
  const warnings = warningsFor(usable, lastRun, now);
  const text = [`Stand: ${formatMoment(finished, now)}`, ...warnings].join(SEPARATOR);
  return { text, warning: warnings.length > 0 };
}

function changedSince(inventoryChangedAt: string | null | undefined, usable: ScanRun): boolean {
  return (
    Boolean(inventoryChangedAt) && new Date(inventoryChangedAt ?? 0) > new Date(usable.startedAt)
  );
}

/** Stand der Daten ohne Rücksicht auf einen laufenden Scan. */
function dataState({ status, now, inventoryChangedAt }: ScanFreshnessInput): ScanFreshnessView {
  const usable = status.lastUsableRun;
  // Mit inventoryChangedAt (auch null) geht es um eine Anwendung: ohne Scan ist sie ungeprüft.
  const perApplication = inventoryChangedAt !== undefined;
  if (!usable && perApplication) return { text: NOT_SCANNED, warning: true };
  if (!usable) return { text: NO_SCAN, warning: status.lastRun?.outcome === "failed" };
  if (changedSince(inventoryChangedAt, usable)) return { text: NOT_SCANNED, warning: true };
  return standFor(usable, status.lastRun, now);
}

function runningState(input: ScanFreshnessInput, startedAt: string): ScanFreshnessView {
  const running = `Scan läuft seit ${timeFormat.format(new Date(startedAt))}`;
  const firstGlobalScan = !input.status.lastUsableRun && input.inventoryChangedAt === undefined;
  if (firstGlobalScan) return { text: running, warning: false };
  const state = dataState(input);
  return { text: [running, state.text].join(SEPARATOR), warning: state.warning };
}

/** Beschreibt, wie aktuell die CVE-Daten sind – global oder für eine Anwendung. */
export function describeScanFreshness(input: ScanFreshnessInput): ScanFreshnessView {
  const { running, startedAt } = input.status;
  if (running && startedAt) return runningState(input, startedAt);
  return dataState(input);
}
