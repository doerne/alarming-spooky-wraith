import { useState } from "react";

import { CveDetailDrawer, CvesPage } from "@/features/cves";
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

type SelectCve = (advisoryId: string) => void;

const PAGES: Record<AppView, (onSelectCve: SelectCve) => React.JSX.Element> = {
  dashboard: (onSelectCve) => <CvesPage onSelectCve={onSelectCve} />,
  inventory: (onSelectCve) => <InventoryPage onSelectCve={onSelectCve} />,
  sources: () => <SourcesPage />,
};

export function App() {
  const [view, setView] = useState<AppView>("dashboard");
  // Gewählte CVE liegt in app/: so öffnen beide Features denselben Drawer,
  // ohne sich gegenseitig zu importieren.
  const [selectedAdvisory, setSelectedAdvisory] = useState<string | null>(null);

  return (
    <SidebarProvider>
      <AppSidebar active={view} onNavigate={setView} />
      <SidebarInset>
        <SiteHeader title={TITLES[view]} />
        <main className="flex flex-1 flex-col gap-6 p-4 md:p-6" data-testid="app-main-content">
          {PAGES[view](setSelectedAdvisory)}
        </main>
        <CveDetailDrawer advisoryId={selectedAdvisory} onClose={() => setSelectedAdvisory(null)} />
      </SidebarInset>
    </SidebarProvider>
  );
}
