import { useState } from "react";

import { ApplicationForm } from "./components/application-form";
import { InventoryForm } from "./components/inventory-form";
import { useAddComponent } from "./hooks/use-add-component";
import { useCreateApplication } from "./hooks/use-create-application";

export function InventoryPage() {
  const [applicationId, setApplicationId] = useState<number | null>(null);
  const createApplication = useCreateApplication();
  const addComponent = useAddComponent();

  return (
    <section className="w-full" data-testid="inventory-section-manage">
      <h2 className="mb-4 text-lg font-semibold">Inventar</h2>
      <ApplicationForm
        onCreate={(values) =>
          createApplication.mutate(values, {
            onSuccess: (application) => setApplicationId(application.id),
          })
        }
      />
      {applicationId !== null && (
        <div className="mt-6" data-testid="inventory-container-component">
          <p className="mb-3 text-sm text-muted-foreground">
            Komponente zu Anwendung #{applicationId} hinzufügen
          </p>
          <InventoryForm onSubmit={(input) => addComponent.mutate({ applicationId, input })} />
        </div>
      )}
    </section>
  );
}
