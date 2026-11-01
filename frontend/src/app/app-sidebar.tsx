import { Boxes, Database, LayoutDashboard, ShieldAlert } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/shared/ui/sidebar";

export type AppView = "dashboard" | "inventory" | "sources";

const ITEMS: ReadonlyArray<{ key: AppView; label: string; icon: LucideIcon }> = [
  { key: "dashboard", label: "Schwachstellen", icon: LayoutDashboard },
  { key: "inventory", label: "Inventar", icon: Boxes },
  { key: "sources", label: "Quellen", icon: Database },
];

interface AppSidebarProps {
  active: AppView;
  onNavigate: (view: AppView) => void;
}

export function AppSidebar({ active, onNavigate }: AppSidebarProps) {
  return (
    <Sidebar data-testid="app-sidebar-main">
      <SidebarHeader>
        <div className="flex items-center gap-2 px-2 py-1.5">
          <ShieldAlert className="size-5 text-primary" aria-hidden />
          <span className="font-semibold">CVE-Radar</span>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {ITEMS.map((item) => (
                <SidebarMenuItem key={item.key}>
                  <SidebarMenuButton
                    isActive={active === item.key}
                    onClick={() => onNavigate(item.key)}
                    tooltip={item.label}
                    data-testid={`app-btn-nav-${item.key}`}
                  >
                    <item.icon aria-hidden />
                    <span>{item.label}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}
