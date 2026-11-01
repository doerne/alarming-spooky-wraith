import { RotateCcw } from "lucide-react";

import { Button } from "@/shared/ui/button";

import type { ApplicationFindingsPage } from "../api/inventory-api";
import { type CveFilters, EMPTY_CVE_FILTERS, hasActiveCveFilters } from "../model/cve-filters";
import { ApplicationCves } from "./application-cves";

interface ApplicationCvesPanelProps {
  page: ApplicationFindingsPage;
  filters: CveFilters;
  onFiltersChange: (filters: CveFilters) => void;
  onSelectCve: (advisoryId: string) => void;
}

/** Ohne Funde nur der Hinweis; sonst Zusammenfassung und Tabelle mit Filtern im Kopf. */
export function ApplicationCvesPanel({
  page,
  filters,
  onFiltersChange,
  onSelectCve,
}: ApplicationCvesPanelProps) {
  const reset = () => onFiltersChange(EMPTY_CVE_FILTERS);
  if (page.unfilteredTotal === 0) {
    return (
      <p className="text-sm text-muted-foreground" data-testid="inventory-text-no-cves">
        Keine Funde für diese Anwendung. Starte einen Scan auf der Schwachstellen-Seite.
      </p>
    );
  }
  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground" data-testid="inventory-text-filter-summary">
          {page.total} von {page.unfilteredTotal} Funden
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={reset}
          disabled={!hasActiveCveFilters(filters)}
          data-testid="inventory-btn-reset-filters"
        >
          <RotateCcw aria-hidden />
          Filter zurücksetzen
        </Button>
      </div>
      <ApplicationCves
        findings={page.items}
        filters={filters}
        onFiltersChange={onFiltersChange}
        onReset={reset}
        onSelect={onSelectCve}
      />
    </>
  );
}
