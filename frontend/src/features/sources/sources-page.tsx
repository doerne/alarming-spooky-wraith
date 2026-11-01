import { useState } from "react";

import { Skeleton } from "@/shared/ui/skeleton";

import { ApiKeyDialog } from "./components/api-key-dialog";
import { SourceTable } from "./components/source-table";
import {
  useRemoveSourceApiKey,
  useSetSourceApiKey,
  useSetSourceEnabled,
  useSources,
} from "./hooks/use-sources";

export function SourcesPage() {
  const sources = useSources();
  const setEnabled = useSetSourceEnabled();
  const setApiKey = useSetSourceApiKey();
  const removeApiKey = useRemoveSourceApiKey();
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const editing = sources.data?.find((source) => source.key === editingKey) ?? null;
  const close = () => setEditingKey(null);

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
      {sources.isError ? (
        <p role="alert" className="text-destructive" data-testid="sources-error-load">
          Quellen konnten nicht geladen werden: {sources.error.message}
        </p>
      ) : null}
      {sources.data ? (
        <SourceTable
          sources={sources.data}
          onToggle={(key, enabled) => setEnabled.mutate({ key, enabled })}
          onEditApiKey={setEditingKey}
        />
      ) : null}
      <ApiKeyDialog
        source={editing}
        onSave={(apiKey) =>
          editingKey && setApiKey.mutate({ key: editingKey, apiKey }, { onSuccess: close })
        }
        onRemove={() => editingKey && removeApiKey.mutate(editingKey, { onSuccess: close })}
        onClose={close}
      />
    </section>
  );
}
