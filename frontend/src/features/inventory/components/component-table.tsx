import { Pencil } from "lucide-react";

import { Button } from "@/shared/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table";

import type { Component } from "../model/types";

const CATEGORY_LABEL: Record<string, string> = {
  language: "Programmiersprache",
  framework: "Framework",
  library: "Library",
  service: "Dienst/Produkt",
};

interface ComponentTableProps {
  components: Component[];
  onEdit: (component: Component) => void;
}

export function ComponentTable({ components, onEdit }: ComponentTableProps) {
  if (components.length === 0) {
    return (
      <p className="text-sm text-muted-foreground" data-testid="inventory-text-no-components">
        Noch keine Komponenten hinterlegt.
      </p>
    );
  }

  return (
    <Table data-testid="inventory-list-components">
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Version</TableHead>
          <TableHead>Kategorie</TableHead>
          <TableHead>Ökosystem</TableHead>
          <TableHead className="w-0 text-right">Aktion</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {components.map((component) => (
          <TableRow key={component.id} data-testid={`inventory-item-component-${component.id}`}>
            <TableCell>{component.name}</TableCell>
            <TableCell>{component.version}</TableCell>
            <TableCell>{CATEGORY_LABEL[component.category] ?? component.category}</TableCell>
            <TableCell>{component.ecosystem ?? "-"}</TableCell>
            <TableCell className="text-right">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => onEdit(component)}
                aria-label={`${component.name} bearbeiten`}
                data-testid={`inventory-btn-edit-${component.id}`}
              >
                <Pencil />
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
