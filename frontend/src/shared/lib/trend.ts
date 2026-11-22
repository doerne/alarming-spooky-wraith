import type { FindingTrend } from "@/shared/api/finding-trend";

export function openNowOf(trend: FindingTrend): number {
  return trend.untouchedNow + trend.inProgressNow;
}

/** Veränderung des offenen Bestands gegenüber dem Zeitraumbeginn. */
export function openDeltaOf(trend: FindingTrend): number {
  return openNowOf(trend) - trend.openAtStart;
}

/** „2026-11-16“ → „16.11.“ */
export function weekLabelOf(weekStart: string): string {
  const [, month, day] = weekStart.split("-");
  return `${day}.${month}.`;
}

export function hasMovement(trend: FindingTrend): boolean {
  return trend.weeks.some((week) => week.new > 0 || week.closed > 0);
}
