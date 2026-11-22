import type { RemediationKpis } from "@/shared/api/remediation-kpis";
import { Badge } from "@/shared/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card";

interface UpdateTargetsCardProps {
  updates: RemediationKpis["updates"];
  feature: string;
  showApplications: boolean;
}

function applicationsLabel(count: number): string {
  return count === 1 ? "in 1 Anwendung" : `in ${count} Anwendungen`;
}

function findingsLabel(count: number): string {
  return count === 1 ? "1 Fund" : `${count} Funde`;
}

export function UpdateTargetsCard({ updates, feature, showApplications }: UpdateTargetsCardProps) {
  return (
    <Card data-testid={`${feature}-card-update-targets`}>
      <CardHeader>
        <CardTitle>Behebbar durch Update</CardTitle>
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
            <ul className="space-y-3" data-testid={`${feature}-list-update-targets`}>
              {updates.targets.map((target, index) => (
                <li
                  key={`${target.ecosystem}-${target.packageName}`}
                  className="flex items-start justify-between gap-3"
                  data-testid={`${feature}-item-update-target-${index}`}
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium" title={target.packageName}>
                      {target.packageName}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {target.ecosystem ?? "–"} · → {target.targetVersion}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1">
                    <Badge variant="secondary" className="shrink-0">
                      {findingsLabel(target.findings)}
                    </Badge>
                    {showApplications && (
                      <p
                        className="text-xs whitespace-nowrap text-muted-foreground"
                        data-testid={`${feature}-text-update-target-applications-${index}`}
                      >
                        {applicationsLabel(target.applications)}
                      </p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
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
