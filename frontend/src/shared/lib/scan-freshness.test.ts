import { describe, expect, it } from "vitest";

import type { ScanRun, ScanStatus } from "@/shared/api/scan-status";

import { describeScanFreshness } from "./scan-freshness";

// Lokale Zeiten, damit die Tests in jeder Zeitzone gleich laufen.
const now = new Date(2026, 10, 22, 10, 0);
const at = (day: number, hour: number, minute: number) =>
  new Date(2026, 10, day, hour, minute).toISOString();
const hoursAgo = (hours: number) => new Date(now.getTime() - hours * 3_600_000).toISOString();

function run(overrides: Partial<ScanRun> = {}): ScanRun {
  return {
    trigger: "schedule",
    outcome: "ok",
    startedAt: at(22, 4, 0),
    finishedAt: at(22, 4, 12),
    componentsScanned: 10,
    findingsFound: 3,
    sourcesWithErrors: 0,
    message: "",
    ...overrides,
  };
}

function status(overrides: Partial<ScanStatus> = {}): ScanStatus {
  return {
    running: false,
    startedAt: null,
    finishedAt: null,
    componentsScanned: null,
    findingsFound: null,
    error: null,
    lastRun: null,
    lastUsableRun: null,
    ...overrides,
  };
}

const describeFor = (value: ScanStatus, inventoryChangedAt?: string | null) =>
  describeScanFreshness({ status: value, now, inventoryChangedAt });

describe("describeScanFreshness", () => {
  it("meldet einen laufenden Scan", () => {
    const value = status({ running: true, startedAt: at(22, 4, 0), lastUsableRun: run() });
    expect(describeFor(value)).toEqual({ text: "Scan läuft seit 04:00", warning: false });
  });

  it("meldet, dass es noch keinen Scan gibt", () => {
    expect(describeFor(status())).toEqual({ text: "Noch kein vollständiger Scan", warning: false });
  });

  it("warnt, wenn bisher nur gescheiterte Läufe da sind", () => {
    const value = status({ lastRun: run({ outcome: "failed" }) });
    expect(describeFor(value)).toEqual({ text: "Noch kein vollständiger Scan", warning: true });
  });

  it("zeigt den Stand von heute", () => {
    const value = status({ lastRun: run(), lastUsableRun: run() });
    expect(describeFor(value)).toEqual({ text: "Stand: heute 04:12", warning: false });
  });

  it("warnt bei Quellen mit Fehlern", () => {
    const incomplete = run({ outcome: "incomplete", sourcesWithErrors: 2 });
    const value = status({ lastRun: incomplete, lastUsableRun: incomplete });
    expect(describeFor(value)).toEqual({
      text: "Stand: heute 04:12 · 2 Quellen mit Fehlern",
      warning: true,
    });
  });

  it("nutzt die Einzahl bei einer Quelle mit Fehlern", () => {
    const incomplete = run({ outcome: "incomplete", sourcesWithErrors: 1 });
    const value = status({ lastRun: incomplete, lastUsableRun: incomplete });
    expect(describeFor(value).text).toBe("Stand: heute 04:12 · 1 Quelle mit Fehlern");
  });

  it("warnt bei einem Stand älter als ein Tag", () => {
    const old = run({ startedAt: at(20, 4, 0), finishedAt: at(20, 4, 9) });
    const value = status({ lastRun: old, lastUsableRun: old });
    expect(describeFor(value)).toEqual({
      text: "Stand: 20.11. 04:09 · älter als ein Tag",
      warning: true,
    });
  });

  it("warnt bei 25 Stunden noch nicht", () => {
    const recent = run({ startedAt: hoursAgo(25.2), finishedAt: hoursAgo(25) });
    const value = status({ lastRun: recent, lastUsableRun: recent });
    expect(describeFor(value).warning).toBe(false);
  });

  it("ergänzt einen neueren fehlgeschlagenen Lauf", () => {
    const failed = run({ outcome: "failed", startedAt: at(22, 8, 0), finishedAt: at(22, 8, 1) });
    const value = status({ lastRun: failed, lastUsableRun: run() });
    expect(describeFor(value)).toEqual({
      text: "Stand: heute 04:12 · letzter Scan fehlgeschlagen",
      warning: true,
    });
  });

  it("meldet ungescannte Änderungen der Anwendung", () => {
    const value = status({ lastRun: run(), lastUsableRun: run() });
    expect(describeFor(value, at(22, 9, 0))).toEqual({
      text: "Noch nicht gescannt – Änderungen seit dem letzten Scan",
      warning: true,
    });
  });

  it("ignoriert Änderungen vor dem letzten Scan", () => {
    const value = status({ lastRun: run(), lastUsableRun: run() });
    expect(describeFor(value, at(21, 9, 0)).text).toBe("Stand: heute 04:12");
  });

  it("zeigt den laufenden Scan auch bei ungescannten Änderungen", () => {
    const value = status({ running: true, startedAt: at(22, 9, 30), lastUsableRun: run() });
    expect(describeFor(value, at(22, 9, 0)).text).toBe("Scan läuft seit 09:30");
  });
});
