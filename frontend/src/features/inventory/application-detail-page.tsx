import { type ReactNode, useMemo, useState } from "react";

import { ApplicationCvesPage } from "./application-cves-page";
import { ApplicationGithubSettings } from "./application-github-settings";
import { ApplicationSbomsPage } from "./application-sboms-page";
import {
  type ApplicationDataCounts,
  DeleteApplicationDialog,
} from "./components/delete-application-dialog";
import { DetailHeader } from "./components/detail-header";
import { DetailTabs } from "./components/detail-tabs";
import { useAddComponent } from "./hooks/use-add-component";
import { useApplication } from "./hooks/use-application";
import { useApplicationFindings } from "./hooks/use-application-findings";
import { useDeleteApplication } from "./hooks/use-delete-application";
import { useSboms } from "./hooks/use-sboms";
import { useUpdateComponent } from "./hooks/use-update-component";
import { EMPTY_CVE_FILTERS } from "./model/cve-filters";
import type { ComponentInput } from "./model/schema";
import type { ApplicationDetail, Component } from "./model/types";
import { Skeleton } from "@/shared/ui/skeleton";

interface ApplicationDetailPageProps {
  applicationId: number;
  onBack: () => void;
  onSelectCve: (advisoryId: string) => void;
}

interface DeleteFlow {
  /** `null`, solange die Anwendung noch nicht geladen ist. */
  open: (() => void) | null;
  dialog: ReactNode;
}

/** Fehlt ein Wert noch, zählt er als 0. */
function countApplicationData(
  application: ApplicationDetail,
  sbomCount: number | undefined,
  findingCount: number | undefined,
): ApplicationDataCounts {
  return {
    components: application.components.length,
    sboms: sbomCount ?? 0,
    findings: findingCount ?? 0,
  };
}

/** Löschen mit Bestätigung; die Zahlen stammen aus Abfragen, die die Seite ohnehin lädt. */
function useDeleteFlow(
  applicationId: number,
  application: ApplicationDetail | undefined,
  onDeleted: () => void,
): DeleteFlow {
  const mutation = useDeleteApplication(applicationId);
  const sboms = useSboms(applicationId);
  const allFindings = useApplicationFindings(applicationId, EMPTY_CVE_FILTERS);
  const [isOpen, setIsOpen] = useState(false);
  if (!application) return { open: null, dialog: null };
  const open = () => {
    mutation.reset();
    setIsOpen(true);
  };
  const dialog = isOpen ? (
    <DeleteApplicationDialog
      name={application.name}
      counts={countApplicationData(
        application,
        sboms.data?.length,
        allFindings.data?.unfilteredTotal,
      )}
      isDeleting={mutation.isPending}
      error={mutation.error?.message ?? null}
      onConfirm={() => mutation.mutate(undefined, { onSuccess: onDeleted })}
      onCancel={() => setIsOpen(false)}
    />
  ) : null;
  return { open, dialog };
}

export function ApplicationDetailPage({
  applicationId,
  onBack,
  onSelectCve,
}: ApplicationDetailPageProps) {
  const detail = useApplication(applicationId);
  const sboms = useSboms(applicationId);
  const sbomNames = useMemo(
    () => new Map((sboms.data ?? []).map((sbom) => [sbom.id, sbom.name])),
    [sboms.data],
  );
  const addComponent = useAddComponent();
  const updateComponent = useUpdateComponent();
  const [editing, setEditing] = useState<Component | null>(null);
  const deletion = useDeleteFlow(applicationId, detail.data, onBack);

  const submitComponent = (input: ComponentInput) => {
    if (editing) {
      updateComponent.mutate(
        { applicationId, componentId: editing.id, input },
        { onSuccess: () => setEditing(null) },
      );
    } else {
      addComponent.mutate({ applicationId, input });
    }
  };

  return (
    <section className="flex flex-col gap-4" data-testid="inventory-section-detail">
      <DetailHeader
        name={detail.data?.name ?? "Anwendung"}
        onBack={onBack}
        onDelete={deletion.open}
        actions={
          <ApplicationGithubSettings applicationId={applicationId} application={detail.data} />
        }
      />
      {detail.isPending ? (
        <Skeleton className="h-40 w-full" />
      ) : (
        <DetailTabs
          components={detail.data?.components ?? []}
          sbomNames={sbomNames}
          sbomsPanel={<ApplicationSbomsPage applicationId={applicationId} />}
          cvesPanel={
            <ApplicationCvesPage applicationId={applicationId} onSelectCve={onSelectCve} />
          }
          editing={editing}
          isSubmitting={addComponent.isPending || updateComponent.isPending}
          onEdit={setEditing}
          onSubmitComponent={submitComponent}
          onCancelEdit={() => setEditing(null)}
        />
      )}
      {deletion.dialog}
    </section>
  );
}
