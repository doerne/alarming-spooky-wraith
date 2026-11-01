import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/ui/tabs";

import type { ComponentInput } from "../model/schema";
import type { ApplicationFinding, Component } from "../model/types";
import { ApplicationCves } from "./application-cves";
import { ComponentsTab } from "./components-tab";

interface DetailTabsProps {
  components: Component[];
  findings: ApplicationFinding[];
  editing: Component | null;
  isSubmitting: boolean;
  onEdit: (component: Component) => void;
  onSubmitComponent: (values: ComponentInput) => void;
  onCancelEdit: () => void;
  onSelectCve: (advisoryId: string) => void;
}

export function DetailTabs({
  components,
  findings,
  editing,
  isSubmitting,
  onEdit,
  onSubmitComponent,
  onCancelEdit,
  onSelectCve,
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
        <ApplicationCves findings={findings} onSelect={onSelectCve} />
      </TabsContent>
    </Tabs>
  );
}
