import { TriangleAlert } from "lucide-react";

import { cn } from "@/shared/lib/utils";
import { Card } from "@/shared/ui/card";

import { TILE_KEYS, type TileKey } from "../model/overview";

interface TileDefinition {
  label: string;
  /** „brennt“ wird rot, „Pflege“ bekommt ein Warn-Icon. */
  kind: "burning" | "care";
}

const TILES: Record<TileKey, TileDefinition> = {
  critical: { label: "Mit kritischen Funden", kind: "burning" },
  overdue: { label: "Mit überfälligen Fristen", kind: "burning" },
  sbom: { label: "SBOM veraltet oder fehlt", kind: "care" },
  unscanned: { label: "Seit Änderung nicht gescannt", kind: "care" },
};

interface OverviewTilesProps {
  counts: Record<TileKey, number>;
  active: TileKey | null;
  onToggle: (tile: TileKey) => void;
}

interface TileProps {
  tile: TileKey;
  count: number;
  active: boolean;
  onToggle: (tile: TileKey) => void;
}

function Tile({ tile, count, active, onToggle }: TileProps) {
  const { label, kind } = TILES[tile];
  const highlighted = count > 0;
  return (
    <Card
      className={cn("p-0", active && "border-primary ring-1 ring-primary")}
      data-testid={`inventory-card-tile-${tile}`}
    >
      <button
        type="button"
        aria-pressed={active}
        onClick={() => onToggle(tile)}
        className="flex h-full w-full flex-col gap-1 rounded-xl p-6 text-left focus-visible:outline-2 focus-visible:outline-ring"
        data-testid={`inventory-btn-tile-${tile}`}
      >
        <span className="text-sm text-muted-foreground">{label}</span>
        <span
          className={cn(
            "flex items-center gap-2 text-3xl font-semibold",
            highlighted && kind === "burning" && "text-destructive",
          )}
          data-testid={`inventory-text-tile-${tile}`}
        >
          {highlighted && kind === "care" ? <TriangleAlert className="size-5" aria-hidden /> : null}
          {count}
        </span>
      </button>
    </Card>
  );
}

/** Summen über alle Anwendungen; ein Klick filtert die Tabelle. */
export function OverviewTiles({ counts, active, onToggle }: OverviewTilesProps) {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {TILE_KEYS.map((tile) => (
        <Tile
          key={tile}
          tile={tile}
          count={counts[tile]}
          active={active === tile}
          onToggle={onToggle}
        />
      ))}
    </div>
  );
}
