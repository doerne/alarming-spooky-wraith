import { Skeleton } from "@/shared/ui/skeleton";

import { ApiKeyDialog } from "./components/api-key-dialog";
import { SourceAlerts } from "./components/source-alerts";
import { SourceTable } from "./components/source-table";
import { useApiKeyEditing } from "./hooks/use-api-key-editing";
import { useSetSourceEnabled, useSources } from "./hooks/use-sources";

export function SourcesPage() {
  const sources = useSources();
  const setEnabled = useSetSourceEnabled();
  const apiKey = useApiKeyEditing(sources.data);

  return (
    <section className="flex flex-col gap-4" data-testid="sources-section-overview">
      <div>
        <h2 className="text-lg font-semibold">Quellen</h2>
        <p className="text-sm text-muted-foreground">
          Öffentliche CVE-Quellen, die der Scan abfragt. Quellen mit Pflicht-Key laufen erst, wenn
          ein API-Key hinterlegt ist.
        </p>
      </div>
      {sources.isPending ? <Skeleton className="h-48 w-full" /> : null}
      <SourceAlerts loadError={sources.error} toggleError={setEnabled.error} />
      {sources.data ? (
        <SourceTable
          sources={sources.data}
          onToggle={(key, enabled) => setEnabled.mutate({ key, enabled })}
          onEditApiKey={apiKey.open}
        />
      ) : null}
      <ApiKeyDialog
        source={apiKey.editing}
        error={apiKey.error}
        onSave={apiKey.save}
        onRemove={apiKey.remove}
        onClose={apiKey.close}
      />
    </section>
  );
}
