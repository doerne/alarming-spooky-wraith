import { z } from "zod";

import { request } from "./http-client";

export const TREND_WEEK_OPTIONS = [4, 12, 26, 52] as const;
export type TrendWeeks = (typeof TREND_WEEK_OPTIONS)[number];
export const DEFAULT_TREND_WEEKS: TrendWeeks = 12;

export const findingTrendSchema = z.object({
  weeks: z.array(
    z.object({
      weekStart: z.string(),
      new: z.number(),
      closed: z.number(),
      openAtEnd: z.number(),
    }),
  ),
  openAtStart: z.number(),
  newTotal: z.number(),
  closedTotal: z.number(),
  untouchedNow: z.number(),
  inProgressNow: z.number(),
  openBySeverityNow: z.record(z.enum(["kritisch", "hoch", "mittel", "niedrig"]), z.number()),
});
export type FindingTrend = z.infer<typeof findingTrendSchema>;

interface FindingTrendParams {
  weeks: TrendWeeks;
  applicationId?: number;
}

export async function fetchFindingTrend({
  weeks,
  applicationId,
}: FindingTrendParams): Promise<FindingTrend> {
  const query = new URLSearchParams({ weeks: String(weeks) });
  if (applicationId !== undefined) {
    query.set("applicationId", String(applicationId));
  }
  return findingTrendSchema.parse(await request(`/api/findings/trend?${query.toString()}`));
}
