import { Pencil } from "lucide-react";

import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table";

import type { Component } from "../model/types";

const CATEGORY_LABEL: Record<string, string> = {
  language: "Programmiersprache",
  framework: "Framework",
  library: "Library",
  service: "Dienst/Produkt",
};

const MANUAL_SOURCE = "manuell";
const UNKNOWN_SBOM = "SBOM";

interface ComponentTableProps {
  components: Component[];
  /** SBOM-ID → Name, um die Quelle einer Komponente anzuzeigen. */
  sbomNames: ReadonlyMap<number, string>;
  onEdit: (component: Component) => void;
}

function sourceOf(component: Component, sbomNames: ReadonlyMap<number, string>): string {
  if (component.sbomId === null) return MANUAL_SOURCE;
  return sbomNames.get(component.sbomId) ?? UNKNOWN_SBOM;
}

function EditButton({
  component,
  onEdit,
}: Pick<ComponentTableProps, "onEdit"> & { component: Component }) {
  if (component.sbomId !== null) return null;
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => onEdit(component)}
      aria-label={`${component.name} bearbeiten`}
      data-testid={`inventory-btn-edit-${component.id}`}
    >
      <Pencil />
    </Button>
  );
}

export function ComponentTable({ components, sbomNames, onEdit }: ComponentTableProps) {
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
          <TableHead>Quelle</TableHead>
          <TableHead className="w-0 text-right">Aktion</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {components.map((component) => (
          <TableRow key={component.id} data-testid={`inventory-item-component-${component.id}`}>
            <TableCell>{component.name}</TableCell>
            <TableCell>{component.version}</TableCell>
            <TableCell>{CATEGORY_LABEL[component.category] ?? component.category}</TableCell>
            <TableCell>
              {component.ecosystem ?? "-"}
              {!component.checked && (
                <Badge
                  variant="secondary"
                  className="ml-2"
                  data-testid={`inventory-text-unchecked-${component.id}`}
                >
                  nicht geprüft
                </Badge>
              )}
            </TableCell>
            <TableCell>{sourceOf(component, sbomNames)}</TableCell>
            <TableCell className="text-right">
              <EditButton component={component} onEdit={onEdit} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
