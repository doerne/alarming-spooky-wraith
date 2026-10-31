import { Button } from "@/shared/ui/button";

import type { Application } from "../model/types";

interface ApplicationListProps {
  applications: Application[];
  onSelect: (applicationId: number) => void;
}

export function ApplicationList({ applications, onSelect }: ApplicationListProps) {
  if (applications.length === 0) {
    return (
      <p className="text-sm text-muted-foreground" data-testid="inventory-text-empty">
        Noch keine Anwendung angelegt.
      </p>
    );
  }

  return (
    <ul className="flex flex-col gap-2" data-testid="inventory-list-applications">
      {applications.map((application) => (
        <li key={application.id}>
          <Button
            variant="outline"
            className="w-full justify-start"
            onClick={() => onSelect(application.id)}
            data-testid={`inventory-item-app-${application.id}`}
          >
            {application.name}
          </Button>
        </li>
      ))}
    </ul>
  );
}
