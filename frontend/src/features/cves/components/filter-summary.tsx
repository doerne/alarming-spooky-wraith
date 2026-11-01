export function FilterSummary({ shown, total }: { shown: number; total: number }) {
  if (shown === 0 && total > 0) {
    return (
      <p className="text-sm text-muted-foreground" data-testid="cves-text-no-results">
        Keine Funde für diese Filter.
      </p>
    );
  }
  return (
    <p className="text-sm text-muted-foreground" data-testid="cves-text-filter-summary">
      {shown} von {total} Funden
    </p>
  );
}
