import { useState } from "react";

import { CvesPage } from "@/features/cves";
import { InventoryPage } from "@/features/inventory";
import { SourcesPage } from "@/features/sources";
import { SidebarInset, SidebarProvider } from "@/shared/ui/sidebar";

import { AppSidebar } from "./app-sidebar";
import type { AppView } from "./app-sidebar";
import { SiteHeader } from "./site-header";

const TITLES: Record<AppView, string> = {
  dashboard: "Schwachstellen",
  inventory: "Inventar",
  sources: "Quellen",
};

const PAGES: Record<AppView, () => React.JSX.Element> = {
  dashboard: CvesPage,
  inventory: InventoryPage,
  sources: SourcesPage,
};

export function App() {
  const [view, setView] = useState<AppView>("dashboard");
  const Page = PAGES[view];

  return (
    <SidebarProvider>
      <AppSidebar active={view} onNavigate={setView} />
      <SidebarInset>
        <SiteHeader title={TITLES[view]} />
        <main className="flex flex-1 flex-col gap-6 p-4 md:p-6" data-testid="app-main-content">
          <Page />
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}
