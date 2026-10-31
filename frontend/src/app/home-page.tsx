import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";

/** Platzhalter-Startseite. Durch das erste Feature ersetzen. */
export function HomePage() {
  return (
    <Card className="w-full max-w-xl" data-testid="home-card-welcome">
      <CardHeader>
        <CardTitle>alarming-spooky-wraith</CardTitle>
        <CardDescription>Projekt ist eingerichtet und bereit für das erste Feature.</CardDescription>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground">
        Features entstehen unter <code>src/features/&lt;name&gt;/</code>.
      </CardContent>
    </Card>
  );
}
