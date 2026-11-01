import { ExternalLink, KeyRound } from "lucide-react";

import { Button } from "@/shared/ui/button";
import { Switch } from "@/shared/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table";

import type { Source } from "../model/types";
import { LastRun } from "./last-run";
import { SourceStatusBadge } from "./source-status-badge";

interface SourceTableProps {
  sources: Source[];
  onToggle: (key: string, enabled: boolean) => void;
  onEditApiKey: (key: string) => void;
}

const KIND_LABEL: Record<Source["kind"], string> = {
  package_query: "Abfrage",
  bulk: "Abzug",
};

function ApiKeyAction({ source, onEdit }: { source: Source; onEdit: (key: string) => void }) {
  if (source.apiKeyRequirement === "none") return null;
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => onEdit(source.key)}
      data-testid={`sources-btn-api-key-${source.key}`}
    >
      <KeyRound aria-hidden />
      {source.hasApiKey ? "Key ändern" : "Key hinterlegen"}
    </Button>
  );
}

function SourceRow({
  source,
  onToggle,
  onEditApiKey,
}: { source: Source } & Omit<SourceTableProps, "sources">) {
  return (
    <TableRow data-testid={`sources-item-${source.key}`}>
      <TableCell className="min-w-64 whitespace-normal">
        <div className="flex flex-col gap-1">
          <a
            href={source.homepageUrl}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 font-medium hover:underline"
            data-testid={`sources-link-homepage-${source.key}`}
          >
            {source.name}
            <ExternalLink className="size-3" aria-hidden />
          </a>
          <span className="text-xs text-muted-foreground">{source.description}</span>
        </div>
      </TableCell>
      <TableCell>{KIND_LABEL[source.kind]}</TableCell>
      <TableCell>
        <SourceStatusBadge sourceKey={source.key} status={source.status} />
      </TableCell>
      <TableCell className="max-w-64 whitespace-normal">
        <LastRun source={source} />
      </TableCell>
      <TableCell>
        <ApiKeyAction source={source} onEdit={onEditApiKey} />
      </TableCell>
      <TableCell className="text-right">
        <Switch
          checked={source.enabled}
          onCheckedChange={(enabled) => onToggle(source.key, enabled)}
          aria-label={`${source.name} aktiv`}
          data-testid={`sources-checkbox-enabled-${source.key}`}
        />
      </TableCell>
    </TableRow>
  );
}

export function SourceTable({ sources, onToggle, onEditApiKey }: SourceTableProps) {
  return (
    <Table data-testid="sources-list-main">
      <TableHeader>
        <TableRow>
          <TableHead>Quelle</TableHead>
          <TableHead>Art</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Letzter Lauf</TableHead>
          <TableHead>API-Key</TableHead>
          <TableHead className="text-right">Aktiv</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {sources.map((source) => (
          <SourceRow
            key={source.key}
            source={source}
            onToggle={onToggle}
            onEditApiKey={onEditApiKey}
          />
        ))}
      </TableBody>
    </Table>
  );
}
