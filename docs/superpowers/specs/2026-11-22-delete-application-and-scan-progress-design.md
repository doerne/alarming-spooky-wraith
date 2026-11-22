# Anwendung löschen und Scan-Fortschritt – Design

Branch: `feat/delete-app-scan-progress` (von `main`)

## Warum

Der Nutzer hat beim Arbeiten mit der App zwei Lücken bemerkt:

1. **Anwendungen lassen sich anlegen, aber nicht wieder entfernen.** Gewünscht ist echtes
   Löschen, also die Anwendung mit allem, was an ihr hängt.
2. **Während eines Scans sieht man nur „Scan läuft …“.** Gewünscht ist ein Statusverlauf,
   der deutlich zeigt, welche Quellen schon erledigt sind. Die Anzeige gehört nur dorthin,
   wo man den Scan startet, also auf die Schwachstellen-Seite neben den Button (vom Nutzer
   entschieden).

## Teil 1: Anwendung löschen

### Verhalten
- In der Detailansicht einer Anwendung (Kopfzeile neben „GitHub“) gibt es den Button
  „Anwendung löschen“ (`variant="destructive"`, Icon `Trash2`).
- Ein Klick öffnet einen Bestätigungsdialog (shadcn `dialog`, schon im Projekt). Er nennt,
  was verloren geht: „<Name> mit N Komponenten, M SBOMs und K Funden endgültig löschen?“,
  dazu den Hinweis „Bereits angelegte GitHub-Issues bleiben auf GitHub bestehen.“ Die
  Buttons heißen „Abbrechen“ und „Endgültig löschen“.
- Nach dem Löschen springt die App zurück zur Inventarliste. Inventar, Schwachstellen,
  Verlauf und Kennzahlen laden neu.
- Läuft gerade ein Scan oder GitHub-Abgleich, ist Löschen gesperrt: Die API antwortet mit
  409, und der Dialog zeigt „Während eines Scans oder GitHub-Abgleichs kann nicht gelöscht werden.“
  (Claudes Entscheidung: Ein Scan hält Komponenten im Speicher und würde sonst Funde zu
  gelöschten Komponenten schreiben wollen.)

### Was gelöscht wird
Funde der Anwendung → Komponenten → SBOM-Versionen und SBOMs → Anwendung, in einer
Transaktion. Advisories, Aliase, Quellen-Einstellungen und das Scan-Protokoll bleiben.
Issues auf GitHub werden nicht angefasst.

### Backend
- Domain-Ports: `ApplicationRepository.delete(application_id)`, dazu die nötigen
  Lösch-Methoden für Funde, Komponenten und SBOMs der Anwendung, soweit noch nicht
  vorhanden.
- Use Case `DeleteApplication(uow, gate).execute(application_id)`:
  `EntityNotFoundError` → 404; Scan oder Abgleich aktiv → neuer Domain-Fehler → 409;
  sonst löschen und `commit()`.
- `DELETE /api/applications/{id}` → 204.
- Tests: Use Case mit Fakes (alles der Anwendung weg, andere Anwendung unberührt,
  Advisory bleibt, 404, Sperre), API-Test 204/404/409, Repository-Test gegen die
  Fremdschlüssel (Reihenfolge).

### Frontend
- Hook `useDeleteApplication` in `features/inventory/hooks`: invalidiert
  `queryKeys.application(id)`, `["applications"]`, `queryKeys.applicationFindings(id)`
  und `queryKeys.findings`.
- Komponente `DeleteApplicationDialog` (rein, Props), Test-IDs `inventory-btn-delete-app`,
  `inventory-dialog-delete-app`, `inventory-btn-confirm-delete-app`, `inventory-error-delete-app`.

## Teil 2: Scan-Fortschritt

### Verhalten
Solange ein Scan läuft, erscheint unter dem Scan-Button auf der Schwachstellen-Seite:

```
Scan läuft · 7 von 21 Quellen erledigt           [██████░░░░░░░░░]
✓ OSV  ✓ GHSA  ✓ NVD  ✓ EUVD  ✓ CVE.org  – Snyk  – OSS Index  ⟳ PyPA  ○ Go  ○ RustSec …
○ Funde speichern   ○ GitHub-Abgleich
```

- **Zustände je Schritt:**
  - wartet `○`
  - läuft `⟳` (drehendes Icon)
  - fertig `✓`
  - übersprungen `–`, z. B. „kein Key“ oder deaktiviert, als Tooltip bzw. `title`
  - Fehler `✕` in `text-destructive`
- **Zähler „X von Y erledigt“:** Erledigt sind fertige, übersprungene und fehlgeschlagene
  Quellen. Y ist die Zahl aller Quellen.
- **Fortschrittsbalken:** Er zeigt den Anteil aller Schritte, also Quellen plus die zwei
  Schlussschritte. Für ihn wird keine shadcn-Komponente ergänzt (keine neue Abhängigkeit),
  sondern ein schlichtes `div` mit `bg-primary` auf `bg-muted` und `role="progressbar"`
  samt `aria-valuenow`.
- **Nach dem Lauf:** Die Anzeige verschwindet und es bleibt die bisherige Anzeige
  („Stand: …“). Bricht der Lauf ab, bleibt der bisherige Fehlerhinweis.
- **Aktualisierung:** Das Polling von `useScanStatus` existiert schon.

### Backend
- `IngestRunState` bekommt `steps: tuple[ScanStep, ...]` mit
  `ScanStep(key, label, state)` und `state ∈ {pending, running, done, skipped, failed}`.
- Der Lauf meldet Fortschritt über einen Callback/Port
  `ScanProgress.update(key, state)`. `RunIngest` ruft ihn je Quelle auf, vorher, nachher
  und mit dem Ergebnis, dann für „Funde speichern“. `run_scan_then_sync` ruft ihn für
  „GitHub-Abgleich“ auf, wenn der Abgleich läuft. Ist GitHub nicht konfiguriert, gilt
  dieser Schritt als übersprungen.
- Zu Beginn des Laufs füllt der Runner alle Schritte mit `pending`: alle Quellen in
  Registry-Reihenfolge, dann `persist`, dann `github-sync`.
- `/api/ingest/status` liefert `steps[{ key, label, state }]`. Labels kommen aus den
  Quellen-Deskriptoren, „Funde speichern“ und „GitHub-Abgleich“ sind fest.
- Thread-Sicherheit: Updates laufen unter dem bestehenden Lock des Runners.
- Tests: `RunIngest` meldet die Schritte in der richtigen Reihenfolge und mit dem
  richtigen Zustand (ok, Fehler, übersprungen) über einen Fake-Callback. Runner-Test für
  den Startzustand (alle `pending`). API-Test, dass `steps` als camelCase-JSON kommt.

### Frontend
- `shared/api/scan-status.ts`: Schema um `steps` erweitern.
- Neue reine Komponente `features/cves/components/scan-progress.tsx`. Sie wird nur
  gerendert, wenn `running` und `steps` nicht leer sind. Test-IDs `cves-card-scan-progress`,
  `cves-text-scan-progress`, `cves-item-scan-step-<key>`.
- `IngestControl` bindet sie unter dem Button ein.

## Nicht-Ziele
- Fortschritt außerhalb der Schwachstellen-Seite (vom Nutzer ausgeschlossen).
- Fortschritt innerhalb einer Quelle (etwa „Komponente 40 von 120“).
- Löschen rückgängig machen oder Papierkorb.
- Schließen oder Kommentieren von GitHub-Issues beim Löschen.

## Ansätze (Fortschritt)

| | Ansatz | Abwägung |
|---|---|---|
| **A (gewählt)** | Der Lauf meldet seine Schritte in den Laufzustand, der Status-Endpoint liefert sie | genau, deckt auch die Schlussschritte ab, wenig Code |
| B | Das Frontend leitet den Fortschritt aus `/api/sources` ab (Status und Zeitpunkt je Quelle) | kein Backend nötig, aber ungenau und ohne Schlussschritte |

Claude hat A gewählt; der Nutzer hat das Wie übergeben.

## Was der Builder entscheidet
- Ob der Fortschritts-Callback als Protocol im `application`-Port oder als
  `Callable[[str, StepState], None]` übergeben wird.
- Genaue Anordnung der Schritt-Chips (Umbruch, Größe), solange sie bei 21 Quellen
  lesbar bleiben.
