import { CvesPage } from "@/features/cves";
import { InventoryPage } from "@/features/inventory";
import { ThemeToggle } from "@/shared/components/theme-toggle";

export function App() {
  return (
    <div className="min-h-svh bg-background">
      <header className="border-b" data-testid="app-header-main">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
          <span className="font-semibold" data-testid="app-text-title">
            alarming-spooky-wraith
          </span>
          <ThemeToggle />
        </div>
      </header>
      <main
        className="mx-auto flex max-w-5xl flex-col gap-10 px-4 py-10"
        data-testid="app-main-content"
      >
        <InventoryPage />
        <CvesPage />
      </main>
    </div>
  );
}
