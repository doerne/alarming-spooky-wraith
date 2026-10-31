import { useState } from "react";
import { ArrowLeft } from "lucide-react";

import { Button } from "@/shared/ui/button";
import { Skeleton } from "@/shared/ui/skeleton";

import { DetailTabs } from "./components/detail-tabs";
import { useAddComponent } from "./hooks/use-add-component";
import { useApplication } from "./hooks/use-application";
import { useApplicationFindings } from "./hooks/use-application-findings";
import { useUpdateComponent } from "./hooks/use-update-component";
import type { ComponentInput } from "./model/schema";
import type { Component } from "./model/types";

interface ApplicationDetailPageProps {
  applicationId: number;
  onBack: () => void;
}

export function ApplicationDetailPage({ applicationId, onBack }: ApplicationDetailPageProps) {
  const detail = useApplication(applicationId);
  const findings = useApplicationFindings(applicationId);
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
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={onBack}
          aria-label="Zurück zur Übersicht"
          data-testid="inventory-btn-back"
        >
          <ArrowLeft />
        </Button>
        <h2 className="text-lg font-semibold" data-testid="inventory-text-app-name">
          {detail.data?.name ?? "Anwendung"}
        </h2>
      </div>
      {detail.isPending ? (
        <Skeleton className="h-40 w-full" />
      ) : (
        <DetailTabs
          components={detail.data?.components ?? []}
          findings={findings.data ?? []}
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
