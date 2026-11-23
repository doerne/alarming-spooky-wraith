export type SeverityLevel = "kritisch" | "hoch" | "mittel" | "niedrig";

/** Badge-Variante je Schweregrad, überall gleich (Funde, Übersicht). */
export const SEVERITY_BADGE_VARIANT: Record<
  SeverityLevel,
  "destructive" | "default" | "secondary" | "outline"
> = {
  kritisch: "destructive",
  hoch: "default",
  mittel: "secondary",
  niedrig: "outline",
};
