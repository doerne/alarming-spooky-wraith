import type { ComponentInput } from "../model/schema";
import type { Component } from "../model/types";
import { ComponentTable } from "./component-table";
import { InventoryForm } from "./inventory-form";

interface ComponentsTabProps {
  components: Component[];
  editing: Component | null;
  isSubmitting: boolean;
  onEdit: (component: Component) => void;
  onSubmit: (values: ComponentInput) => void;
  onCancelEdit: () => void;
}

function toInput(component: Component): ComponentInput {
  return {
    name: component.name,
    version: component.version,
    category: component.category as ComponentInput["category"],
    ecosystem: component.ecosystem as ComponentInput["ecosystem"],
    direct: component.direct,
  };
}

export function ComponentsTab({
  components,
  editing,
  isSubmitting,
  onEdit,
  onSubmit,
  onCancelEdit,
}: ComponentsTabProps) {
  return (
    <div className="flex flex-col gap-6 pt-4">
      <ComponentTable components={components} onEdit={onEdit} />
      <div data-testid="inventory-container-component-form">
        <p className="mb-3 text-sm font-medium" data-testid="inventory-text-form-title">
          {editing ? "Komponente bearbeiten" : "Komponente hinzufügen"}
        </p>
        <InventoryForm
          key={editing?.id ?? "new"}
          initialValues={editing ? toInput(editing) : undefined}
          submitLabel={editing ? "Änderungen speichern" : "Komponente hinzufügen"}
          isSubmitting={isSubmitting}
          onSubmit={onSubmit}
          onCancel={editing ? onCancelEdit : undefined}
        />
      </div>
    </div>
  );
}
