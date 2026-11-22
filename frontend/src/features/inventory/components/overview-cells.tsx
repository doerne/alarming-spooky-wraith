import { TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";

import { SEVERITY_BADGE_VARIANT } from "@/shared/lib/severity";
import { Badge } from "@/shared/ui/badge";

import { type ApplicationOverview, OVERVIEW_SEVERITIES, sbomAgeText } from "../model/overview";

interface TextProps {
  children: ReactNode;
  testId?: string;
}

function Muted({ children, testId }: TextProps) {
  return (
    <span className="text-muted-foreground" data-testid={testId}>
      {children}
    </span>
  );
}

/** Pflege-Hinweis: normale Textfarbe mit Warn-Icon (das Theme hat keine Warnfarbe). */
function Warning({ children, testId }: TextProps) {
  return (
    <span className="inline-flex items-center gap-1" data-testid={testId}>
      <TriangleAlert className="size-4" aria-hidden />
      {children}
    </span>
  );
}

export function OpenCell({ row }: { row: ApplicationOverview }) {
  const total = OVERVIEW_SEVERITIES.reduce((sum, level) => sum + row.openBySeverity[level], 0);
  if (total === 0) return <Muted>keine</Muted>;
  return (
    <span className="flex gap-1">
      {OVERVIEW_SEVERITIES.map((level) => (
        <Badge
          key={level}
          variant={SEVERITY_BADGE_VARIANT[level]}
          title={level}
          data-testid={`inventory-badge-open-${level}-${row.id}`}
        >
          <span className="sr-only">{level} </span>
          {row.openBySeverity[level]}
        </Badge>
      ))}
    </span>
  );
}

export function SbomCell({ row, now }: { row: ApplicationOverview; now: Date }) {
  const testId = `inventory-text-sbom-${row.id}`;
  if (row.latestSbomUploadAt === null) {
    return <Muted testId={testId}>keine SBOM</Muted>;
  }
  const age = sbomAgeText(row.latestSbomUploadAt, now);
  if (!row.sbomStale) return <span data-testid={testId}>{age}</span>;
  return <Warning testId={testId}>{age}</Warning>;
}

const dayFormat = new Intl.DateTimeFormat("de-DE", { day: "2-digit", month: "2-digit" });

export function ScanCell({ row }: { row: ApplicationOverview }) {
  if (row.scanState === "never_scanned") return <Warning>Noch kein Scan</Warning>;
  if (row.scanState === "current") return <Muted>aktuell</Muted>;
  if (row.inventoryChangedAt === null) return <Warning>Seit Änderung nicht gescannt</Warning>;
  return <Warning>seit {dayFormat.format(new Date(row.inventoryChangedAt))} geändert</Warning>;
}
