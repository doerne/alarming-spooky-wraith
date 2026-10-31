import { ThemeToggle } from "@/shared/components/theme-toggle";
import { Separator } from "@/shared/ui/separator";
import { SidebarTrigger } from "@/shared/ui/sidebar";

export function SiteHeader({ title }: { title: string }) {
  return (
    <header
      className="flex h-14 shrink-0 items-center gap-2 border-b px-4"
      data-testid="app-header-main"
    >
      <SidebarTrigger data-testid="app-btn-sidebar-toggle" />
      <Separator orientation="vertical" className="mr-2 h-4" />
      <span className="font-semibold" data-testid="app-text-title">
        {title}
      </span>
      <div className="ml-auto">
        <ThemeToggle />
      </div>
    </header>
  );
}
