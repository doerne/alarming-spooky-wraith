import type { RemediationKpis } from "@/shared/api/remediation-kpis";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table";

interface UpdateTargetsCardProps {
  updates: RemediationKpis["updates"];
  feature: string;
  showApplications: boolean;
}

export function UpdateTargetsCard({ updates, feature, showApplications }: UpdateTargetsCardProps) {
  return (
    <Card data-testid={`${feature}-card-update-targets`}>
      <CardHeader>
        <CardTitle>Updates mit größtem Effekt</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {updates.targets.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Kein offener Fund mit bekannter Fix-Version.
          </p>
        ) : (
          <>
            <p className="text-sm text-muted-foreground" data-testid={`${feature}-text-fixable`}>
              {updates.fixableOpen} von {updates.openTotal} offenen Funden durch Update behebbar
            </p>
            <Table data-testid={`${feature}-list-update-targets`}>
              <TableHeader>
                <TableRow>
                  <TableHead>Paket</TableHead>
                  <TableHead>Zielversion</TableHead>
                  <TableHead className="text-right">Funde</TableHead>
                  {showApplications && <TableHead className="text-right">Anwendungen</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {updates.targets.map((target, index) => (
                  <TableRow
                    key={`${target.ecosystem}-${target.packageName}`}
                    data-testid={`${feature}-item-update-target-${index}`}
                  >
                    <TableCell className="font-medium">{target.packageName}</TableCell>
                    <TableCell>{target.targetVersion}</TableCell>
                    <TableCell className="text-right">{target.findings}</TableCell>
                    {showApplications && (
                      <TableCell className="text-right">{target.applications}</TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {updates.morePackages > 0 && (
              <p className="text-sm text-muted-foreground">
                + {updates.morePackages} weitere Pakete
              </p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
