interface SourceAlertsProps {
  loadError: Error | null;
  toggleError: Error | null;
}

export function SourceAlerts({ loadError, toggleError }: SourceAlertsProps) {
  return (
    <>
      {loadError ? (
        <p role="alert" className="text-destructive" data-testid="sources-error-load">
          Quellen konnten nicht geladen werden: {loadError.message}
        </p>
      ) : null}
      {toggleError ? (
        <p role="alert" className="text-destructive" data-testid="sources-error-toggle">
          Quelle konnte nicht umgeschaltet werden: {toggleError.message}
        </p>
      ) : null}
    </>
  );
}
