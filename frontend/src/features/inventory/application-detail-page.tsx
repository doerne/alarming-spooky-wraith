import { useMemo, useState } from "react";

import { ApplicationCvesPage } from "./application-cves-page";
import { ApplicationGithubSettings } from "./application-github-settings";
import { ApplicationSbomsPage } from "./application-sboms-page";
import { DetailHeader } from "./components/detail-header";
import { DetailTabs } from "./components/detail-tabs";
import { useAddComponent } from "./hooks/use-add-component";
import { useApplication } from "./hooks/use-application";
import { useSboms } from "./hooks/use-sboms";
import { useUpdateComponent } from "./hooks/use-update-component";
import type { ComponentInput } from "./model/schema";
import type { Component } from "./model/types";
import { Skeleton } from "@/shared/ui/skeleton";

interface ApplicationDetailPageProps {
  applicationId: number;
  onBack: () => void;
  onSelectCve: (advisoryId: string) => void;
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
    </section>
  );
}
