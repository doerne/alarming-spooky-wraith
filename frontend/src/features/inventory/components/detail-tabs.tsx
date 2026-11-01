import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/ui/tabs";

import type { ComponentInput } from "../model/schema";
import type { ReactNode } from "react";

import type { Component } from "../model/types";
import { ComponentsTab } from "./components-tab";

interface DetailTabsProps {
  components: Component[];
  cvesPanel: ReactNode;
  editing: Component | null;
  isSubmitting: boolean;
  onEdit: (component: Component) => void;
  onSubmitComponent: (values: ComponentInput) => void;
  onCancelEdit: () => void;
}

export function DetailTabs({
  components,
  cvesPanel,
  editing,
  isSubmitting,
  onEdit,
  onSubmitComponent,
  onCancelEdit,
}: DetailTabsProps) {
  return (
    <Tabs defaultValue="components" data-testid="inventory-tab-detail">
      <TabsList>
        <TabsTrigger value="components" data-testid="inventory-tab-components">
          Komponenten
        </TabsTrigger>
        <TabsTrigger value="cves" data-testid="inventory-tab-cves">
          CVEs
        </TabsTrigger>
      </TabsList>
      <TabsContent value="components">
        <ComponentsTab
          components={components}
          editing={editing}
          isSubmitting={isSubmitting}
          onEdit={onEdit}
          onSubmit={onSubmitComponent}
          onCancelEdit={onCancelEdit}
        />
      </TabsContent>
      <TabsContent value="cves" className="pt-4">
        {cvesPanel}
      </TabsContent>
    </Tabs>
  );
}
