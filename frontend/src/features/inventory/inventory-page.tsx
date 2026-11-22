import { Plus } from "lucide-react";
import { useState } from "react";

import { ScanFreshness } from "@/shared/components/scan-freshness";
import { describeScanFreshness, type ScanFreshnessView } from "@/shared/lib/scan-freshness";
import { Button } from "@/shared/ui/button";
import { Skeleton } from "@/shared/ui/skeleton";

import { ApplicationDetailPage } from "./application-detail-page";
import { CreateApplicationDialog } from "./components/create-application-dialog";
import { OverviewSection } from "./components/overview-section";
import { useApplicationsOverview } from "./hooks/use-applications-overview";
import { useCreateApplication } from "./hooks/use-create-application";
import { useScanStatus } from "./hooks/use-scan-status";
import {
  DEFAULT_OVERVIEW_SORT,
  nextOverviewSort,
  type SortKey,
  type TileKey,
} from "./model/overview";

function OverviewHeader({
  freshness,
  onCreate,
}: {
  freshness: ScanFreshnessView | null;
  onCreate: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex flex-col gap-1">
        <h2 className="text-lg font-semibold">Inventar</h2>
        {freshness ? (
          <ScanFreshness
            text={freshness.text}
            warning={freshness.warning}
            testId="inventory-text-scan-freshness"
          />
        ) : null}
      </div>
      <Button onClick={onCreate} data-testid="inventory-btn-open-create-app">
        <Plus aria-hidden /> Anwendung anlegen
      </Button>
    </div>
  );
}

function useFreshness(): ScanFreshnessView | null {
  const scanStatus = useScanStatus();
  return scanStatus.data
    ? describeScanFreshness({ status: scanStatus.data, now: new Date() })
    : null;
}

function useOverviewControls() {
  const [tile, setTile] = useState<TileKey | null>(null);
  const [sort, setSort] = useState(DEFAULT_OVERVIEW_SORT);
  return {
    tile,
    sort,
    onToggleTile: (next: TileKey) => setTile((current) => (current === next ? null : next)),
    onResetTile: () => setTile(null),
    onSort: (key: SortKey) => setSort((current) => nextOverviewSort(current, key)),
  };
}

export function InventoryPage({ onSelectCve }: { onSelectCve: (advisoryId: string) => void }) {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const overview = useApplicationsOverview();
  const createApplication = useCreateApplication();
  const controls = useOverviewControls();
  const freshness = useFreshness();

  if (selectedId !== null) {
    return (
      <ApplicationDetailPage
        applicationId={selectedId}
        onBack={() => setSelectedId(null)}
        onSelectCve={onSelectCve}
      />
    );
  }

  const create = (values: { name: string }) =>
    createApplication.mutate(values, {
      onSuccess: (application) => {
        setCreating(false);
        setSelectedId(application.id);
      },
    });

  return (
    <section className="flex flex-col gap-6" data-testid="inventory-section-manage">
      <OverviewHeader
        freshness={freshness}
        onCreate={() => {
          createApplication.reset();
          setCreating(true);
        }}
      />
      {overview.isPending ? (
        <Skeleton className="h-64 w-full" data-testid="inventory-skeleton-overview" />
      ) : null}
      {overview.isError ? (
        <p role="alert" className="text-sm text-destructive" data-testid="inventory-error-overview">
          Die Übersicht konnte nicht geladen werden.
        </p>
      ) : null}
      {overview.data ? (
        <OverviewSection
          rows={overview.data}
          now={new Date()}
          onSelect={setSelectedId}
          {...controls}
        />
      ) : null}
      <CreateApplicationDialog
        open={creating}
        onOpenChange={setCreating}
        onCreate={create}
        isCreating={createApplication.isPending}
        error={createApplication.error?.message ?? null}
      />
    </section>
  );
}
