import { type UseQueryResult } from "@tanstack/react-query";
import { useState } from "react";
import { Upload } from "lucide-react";

import { Button } from "@/shared/ui/button";
import { Skeleton } from "@/shared/ui/skeleton";

import { SbomDeleteDialog } from "./components/sbom-delete-dialog";
import { SbomHistoryDialog } from "./components/sbom-history-dialog";
import { SbomList, type SbomListProps } from "./components/sbom-list";
import { SbomUploadDialog } from "./components/sbom-upload-dialog";
import { SbomUploadResultText } from "./components/sbom-upload-result";
import { useDeleteSbom } from "./hooks/use-delete-sbom";
import { useSbomVersion } from "./hooks/use-sbom-version";
import { useSbomVersions } from "./hooks/use-sbom-versions";
import { useSboms } from "./hooks/use-sboms";
import { useUploadSbom } from "./hooks/use-upload-sbom";
import type { SbomSummary, SbomUploadBody } from "./model/sbom-types";

interface ApplicationSbomsPageProps {
  applicationId: number;
}

/** `fixedName` null = neue SBOM, sonst neue Version dieser SBOM. */
interface UploadTarget {
  fixedName: string | null;
}

function closeHandler(onClose: () => void) {
  return (open: boolean) => {
    if (!open) onClose();
  };
}

function useUploadFlow(applicationId: number) {
  const mutation = useUploadSbom(applicationId);
  const [target, setTarget] = useState<UploadTarget | null>(null);
  const open = (fixedName: string | null) => {
    mutation.reset();
    setTarget({ fixedName });
  };
  const submit = (body: SbomUploadBody) =>
    mutation.mutate(body, { onSuccess: () => setTarget(null) });
  const dialog = (
    <SbomUploadDialog
      open={target !== null}
      fixedName={target?.fixedName ?? null}
      isSubmitting={mutation.isPending}
      error={mutation.error?.message ?? null}
      onSubmit={submit}
      onOpenChange={closeHandler(() => setTarget(null))}
    />
  );
  const result = target === null && mutation.data ? mutation.data : null;
  return { open, dialog, result };
}

function useHistoryFlow(applicationId: number) {
  const [sbom, setSbom] = useState<SbomSummary | null>(null);
  const [versionId, setVersionId] = useState<number | null>(null);
  const versions = useSbomVersions(applicationId, sbom?.id ?? null);
  const selectedRef = sbom && versionId !== null ? { sbomId: sbom.id, versionId } : null;
  const selected = useSbomVersion(applicationId, selectedRef);
  const open = (target: SbomSummary) => {
    setSbom(target);
    setVersionId(null);
  };
  const dialog = sbom && (
    <SbomHistoryDialog
      sbom={sbom}
      versions={versions.data ?? []}
      selected={selected.data ?? null}
      onSelect={setVersionId}
      onOpenChange={closeHandler(() => setSbom(null))}
    />
  );
  return { open, dialog };
}

function useDeleteFlow(applicationId: number) {
  const mutation = useDeleteSbom(applicationId);
  const [target, setTarget] = useState<SbomSummary | null>(null);
  const confirm = (sbom: SbomSummary) =>
    mutation.mutate(sbom.id, { onSuccess: () => setTarget(null) });
  const open = (sbom: SbomSummary) => {
    mutation.reset();
    setTarget(sbom);
  };
  const dialog = target && (
    <SbomDeleteDialog
      sbom={target}
      isDeleting={mutation.isPending}
      error={mutation.error?.message ?? null}
      onConfirm={confirm}
      onCancel={() => setTarget(null)}
    />
  );
  return { open, dialog };
}

interface SbomListStateProps extends Omit<SbomListProps, "sboms"> {
  query: UseQueryResult<SbomSummary[]>;
}

function SbomListState({ query, ...handlers }: SbomListStateProps) {
  if (query.isPending) return <Skeleton className="h-24 w-full" />;
  if (query.isError) {
    return (
      <p role="alert" className="text-sm text-destructive" data-testid="inventory-error-sboms-load">
        SBOMs konnten nicht geladen werden: {query.error.message}
      </p>
    );
  }
  return <SbomList sboms={query.data} {...handlers} />;
}

/** Container des SBOM-Reiters: Liste, Upload, Verlauf und Löschen. */
export function ApplicationSbomsPage({ applicationId }: ApplicationSbomsPageProps) {
  const sboms = useSboms(applicationId);
  const upload = useUploadFlow(applicationId);
  const history = useHistoryFlow(applicationId);
  const removal = useDeleteFlow(applicationId);

  return (
    <section className="flex flex-col gap-4 pt-4" data-testid="inventory-card-sboms-panel">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          CycloneDX-JSON je Anwendung. Geprüft wird nur die aktuelle Version jeder SBOM.
        </p>
        <Button onClick={() => upload.open(null)} data-testid="inventory-btn-sbom-upload">
          <Upload /> SBOM hochladen
        </Button>
      </div>
      {upload.result && <SbomUploadResultText result={upload.result} />}
      <SbomListState
        query={sboms}
        onUploadVersion={(sbom) => upload.open(sbom.name)}
        onShowHistory={history.open}
        onDelete={removal.open}
      />
      {upload.dialog}
      {history.dialog}
      {removal.dialog}
    </section>
  );
}
