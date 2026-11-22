import { Button } from "@/shared/ui/button";

import {
  type ApplicationOverview,
  filterOverview,
  type OverviewSort,
  type SortKey,
  sortOverview,
  summarizeOverview,
  type TileKey,
} from "../model/overview";
import { OverviewTable } from "./overview-table";
import { OverviewTiles } from "./overview-tiles";

export interface OverviewSectionProps {
  rows: ApplicationOverview[];
  tile: TileKey | null;
  sort: OverviewSort;
  now: Date;
  onToggleTile: (tile: TileKey) => void;
  onResetTile: () => void;
  onSort: (key: SortKey) => void;
  onSelect: (applicationId: number) => void;
}

function FilterEmpty({ onReset }: { onReset: () => void }) {
  return (
    <div className="flex items-center gap-3">
      <p className="text-sm text-muted-foreground" data-testid="inventory-text-filter-empty">
        Keine Anwendung in dieser Auswahl.
      </p>
      <Button
        variant="outline"
        size="sm"
        onClick={onReset}
        data-testid="inventory-btn-reset-filter"
      >
        Filter zurücksetzen
      </Button>
    </div>
  );
}

type OverviewBodyProps = Pick<
  OverviewSectionProps,
  "rows" | "sort" | "now" | "onResetTile" | "onSort" | "onSelect"
> & { visible: ApplicationOverview[] };

function OverviewBody({ rows, visible, ...props }: OverviewBodyProps) {
  if (rows.length === 0) {
    return (
      <p className="text-sm text-muted-foreground" data-testid="inventory-text-empty">
        Noch keine Anwendung angelegt.
      </p>
    );
  }
  if (visible.length === 0) return <FilterEmpty onReset={props.onResetTile} />;
  return (
    <OverviewTable
      rows={visible}
      sort={props.sort}
      now={props.now}
      onSort={props.onSort}
      onSelect={props.onSelect}
    />
  );
}

/** Kacheln und Tabelle; Filtern und Sortieren steuert die Seite. */
export function OverviewSection(props: OverviewSectionProps) {
  const { rows, tile, sort } = props;
  const visible = sortOverview(filterOverview(rows, tile), sort);
  return (
    <>
      <OverviewTiles counts={summarizeOverview(rows)} active={tile} onToggle={props.onToggleTile} />
      <OverviewBody
        rows={rows}
        visible={visible}
        sort={sort}
        now={props.now}
        onResetTile={props.onResetTile}
        onSort={props.onSort}
        onSelect={props.onSelect}
      />
    </>
  );
}
