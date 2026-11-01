import { useState } from "react";

import { ApplicationDetailPage } from "./application-detail-page";
import { ApplicationForm } from "./components/application-form";
import { ApplicationList } from "./components/application-list";
import { useApplications } from "./hooks/use-applications";
import { useCreateApplication } from "./hooks/use-create-application";

export function InventoryPage({ onSelectCve }: { onSelectCve: (advisoryId: string) => void }) {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const applications = useApplications();
  const createApplication = useCreateApplication();

  if (selectedId !== null) {
    return (
      <ApplicationDetailPage
        applicationId={selectedId}
        onBack={() => setSelectedId(null)}
        onSelectCve={onSelectCve}
      />
    );
  }

  return (
    <section className="flex flex-col gap-6" data-testid="inventory-section-manage">
      <ApplicationForm
        onCreate={(values) =>
          createApplication.mutate(values, {
            onSuccess: (application) => setSelectedId(application.id),
          })
        }
      />
      <ApplicationList applications={applications.data ?? []} onSelect={setSelectedId} />
    </section>
  );
}
