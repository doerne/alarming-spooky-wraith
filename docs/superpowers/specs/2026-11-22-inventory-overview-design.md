# Inventar-Übersicht mit Kennzahlen – Design

Branch: `feat/inventory-overview`, abgezweigt von `feat/delete-app-scan-progress`, weil das
Löschen und die zentralen Query-Keys von dort gebraucht werden (Claudes Entscheidung). Nach
dem Merge von PR #19 wird auf `main` umgehängt.

## Warum

Die Inventar-Seite zeigt heute nur ein Formular „Anwendung anlegen“ und eine Liste mit den
Namen der Anwendungen als Knöpfe. Wer wissen will, wie es um eine Anwendung steht, muss sie
öffnen und den CVE-Reiter lesen.

Der Nutzer will auf der Übersicht **beides** auf einen Blick erkennen:

1. **Wo es brennt:** Anwendungen mit offenen kritischen Funden oder überfälligen Fristen.
2. **Ob alles gepflegt ist:** Anwendungen ohne aktuelle SBOM oder mit Änderungen, die noch
   nicht gescannt sind.

## Ziele, Nicht-Ziele, Anti-Ziele

- **Ziele:**
  - Oben Summen-Kacheln über alle Anwendungen, darunter eine sortierbare Tabelle mit einer
    Zeile je Anwendung (Variante C, vom Nutzer gewählt).
  - Ein Klick auf eine Kachel filtert die Tabelle auf die betroffenen Anwendungen.
  - Ein Klick auf eine Zeile öffnet die Detailansicht wie bisher.
- **Nicht-Ziele:**
  - Verlauf oder Diagramme je Anwendung in der Tabelle (die gibt es in der Detailansicht).
  - Paginierung, serverseitiges Sortieren und Export.
  - Änderungen an der Detailansicht.
- **Anti-Ziele:**
  - Die Übersicht wird mit der Zahl der Anwendungen langsam (N+1-Abfragen).
  - Zahlen in der Übersicht weichen von denen der Detailansicht ab, etwa bei offenen Funden
    oder Überfälligen.

## Ansätze

1. **Neuer Endpoint `GET /api/applications/overview`** – ein Use Case rechnet alle
   Kennzahlen in einem Durchgang, das Frontend bekommt eine fertige Liste.
   **Vom Nutzer gewählt.** Ein Request, die Fachregeln (Fristen, „Noch nicht gescannt“)
   bleiben im Backend.
2. `GET /api/applications` um die Zahlen erweitern – verworfen: Die Liste würde für alle
   Aufrufer teurer und nach jedem Scan veralten.
3. Im Frontend aus den bestehenden Endpoints zusammensetzen – verworfen: vier Requests je
   Anwendung, doppelte Logik im Frontend, passt nicht zur Architektur.

## Verhalten

### Kopf
- Überschrift „Inventar“ und rechts der Button „Anwendung anlegen“ (Icon `Plus`).
- Der Button öffnet einen Dialog (shadcn `dialog`) mit dem bisherigen Formular. Nach dem
  Anlegen öffnet sich wie bisher die Detailansicht der neuen Anwendung.
  (Claudes Entscheidung: Das Formular über der Liste würde die Kacheln nach unten drücken.)

### Summen-Kacheln (vier, nebeneinander; auf schmalen Bildschirmen zwei je Zeile)
| Kachel | zählt Anwendungen, bei denen … |
|---|---|
| „Mit kritischen Funden“ | mindestens ein offener Fund die Stufe kritisch hat |
| „Mit überfälligen Fristen“ | mindestens ein offener Fund überfällig ist |
| „SBOM veraltet oder fehlt“ | keine SBOM existiert oder die neueste Version älter als 30 Tage ist |
| „Seit Änderung nicht gescannt“ | sich das Inventar nach Beginn des letzten verwertbaren Scans geändert hat oder noch nie ein verwertbarer Scan lief |

- Die ersten beiden Kacheln sind „brennt“, die anderen „Pflege“. Ist der Wert größer als 0,
  wird „brennt“ in `text-destructive` hervorgehoben. „Pflege“ bleibt in der normalen
  Textfarbe und bekommt das Icon `TriangleAlert`. Bei 0 bleibt die Zahl neutral, ohne Icon.
  Das Haus-Theme bleibt unverändert, es kommt kein Warn-Token dazu (vom Nutzer entschieden).
- Ein Klick auf eine Kachel filtert die Tabelle. Es ist immer höchstens ein Filter aktiv,
  die aktive Kachel ist sichtbar markiert (`aria-pressed`). Ein zweiter Klick oder
  „Filter zurücksetzen“ zeigt wieder alle. (Claudes Entscheidung: Ein einzelner Filter
  reicht für die Frage „welche sind das?“.)
- Die 30 Tage sind Claudes Entscheidung. Eine SBOM, die einen Monat nicht erneuert wurde,
  ist bei aktiver Entwicklung ein Zeichen fehlender Pipeline. Anwendungen, die nur von Hand
  gepflegt werden (keine SBOM), zählen bewusst mit, weil „gepflegt“ hier heißt, dass das
  Inventar automatisch aktuell gehalten wird.

### Tabelle (shadcn `table`)
Spalten:
| Spalte | Inhalt |
|---|---|
| Anwendung | Name, darunter die Beschreibung gedämpft und auf eine Zeile gekürzt |
| Offen | vier kleine Zähler kritisch / hoch / mittel / niedrig (wie die Schweregrad-Badges der Schwachstellen-Seite); bei 0 offenen Funden „keine“ gedämpft |
| Überfällig | Anzahl; > 0 in `text-destructive` |
| Komponenten | Anzahl der aktiven (nicht ausgebauten) Komponenten |
| SBOM | „vor N Tagen“ (neueste Version über alle SBOMs der Anwendung), „keine SBOM“ gedämpft; veraltet mit `TriangleAlert` |
| Gescannt | „aktuell“ gedämpft; „seit TT.MM. geändert“ mit `TriangleAlert`, wenn das Inventar nach Beginn des letzten verwertbaren Scans geändert wurde; „Noch kein Scan“ mit `TriangleAlert` |
| GitHub | Repository-Name oder „–“ |

- Ein Scan läuft immer über alle Anwendungen. Den globalen Stand („Stand: heute 04:12 …“)
  zeigt deshalb einmal die vorhandene `ScanFreshness`-Zeile über der Tabelle und nicht
  jede Zeile (Claudes Entscheidung nach dem Builder-Check).
- **Sortierung:** Jeder Spaltenkopf ist ein Button, ein Klick sortiert, ein zweiter dreht
  die Richtung um. Der Pfeil zeigt die aktive Spalte und Richtung (`aria-sort`).
- **Standard** („kritischste zuerst“): offene kritische absteigend, dann hohe, mittlere und
  niedrige absteigend, dann Überfällige absteigend, zuletzt der Name aufsteigend.
- „Offen“ sortiert nach derselben Schweregrad-Reihenfolge. „SBOM“ sortiert ältere oder
  fehlende zuerst bei absteigender Richtung. „Gescannt“ sortiert bei absteigender Richtung
  „Noch kein Scan“, dann „geändert“ (ältere Änderung zuerst), dann „aktuell“.
- Die ganze Zeile ist klickbar und per Tastatur erreichbar: Der Name ist ein Button, der die
  Detailansicht öffnet.
- **Leerzustände:** Ohne Anwendungen erscheint „Noch keine Anwendung angelegt.“ mit dem
  Anlegen-Button, die Kacheln zeigen 0. Bleibt durch einen Filter nichts übrig, erscheint
  „Keine Anwendung in dieser Auswahl.“ mit „Filter zurücksetzen“.
- **Laden und Fehler:** Beim Laden stehen `Skeleton` für Kacheln und Tabelle. Bei einem
  Fehler erscheint eine Meldung mit `role="alert"`.

## Backend

### Domain
- Neues Modul `domain/application_overview.py`, rein und ohne Framework:
  - `SBOM_STALE_AFTER_DAYS = 30`.
  - `ScanState(StrEnum)`: `current`, `changed_since_scan`, `never_scanned`.
  - `scan_state(inventory_changed_at, last_usable_scan_started_at) -> ScanState`, dieselbe
    Regel wie die Frontend-Logik „Noch nicht gescannt“ (`shared/lib/scan-freshness.ts`):
    geändert nach Beginn des letzten verwertbaren Laufs.
  - `is_sbom_stale(latest_upload, now) -> bool`: True, wenn keine SBOM existiert oder sie
    älter als 30 Tage ist.
  - Dataclass `ApplicationOverview` mit `application_id`, `name`, `description`,
    `open_by_severity: dict[Severity, int]` (immer alle vier Stufen), `overdue`,
    `component_count`, `latest_sbom_upload_at`, `sbom_stale`, `scan_state`,
    `inventory_changed_at`, `github_repository`.
- Offene Funde und Überfällige rechnet die Domain mit den vorhandenen Funktionen
  (`is_closed`, `compute_deadlines`). So stimmen die Zahlen mit der Detailansicht überein.

### Application
- Use Case `GetApplicationsOverview(uow, clock).execute() -> list[ApplicationOverview]`.
- Er lädt Anwendungen, Komponenten und Funde jeweils einmal für alle Anwendungen, dazu die
  SBOMs und den letzten verwertbaren Lauf, und gruppiert im Speicher nach
  `application_id`. Fehlt dafür eine Repository-Methode (etwa die neueste SBOM-Version je
  Anwendung), kommt sie in den Port, ohne Schleife mit einer Abfrage je Anwendung.
- `component_count` zählt nur aktive (nicht ausgebaute) Komponenten, wie der
  Komponenten-Reiter.
- Offene Funde und Überfällige zählen **alle** nicht erledigten Funde der Anwendung, auch auf
  ausgebauten Komponenten. So rechnen `ListFindings` und `GetRemediationKpis` in der
  Detailansicht. Solche Funde räumt erst der nächste Scan auf (`ResolveRetiredFindings`).
  Die Zahlen stimmen damit mit der Detailansicht überein (Claudes Entscheidung nach dem
  Builder-Check, wegen des Anti-Ziels).

### Presentation
- `GET /api/applications/overview` → `list[ApplicationOverviewResponse]` (camelCase über
  `ApiModel`). `openBySeverity` ist ein Objekt mit den Schlüsseln `kritisch`, `hoch`,
  `mittel` und `niedrig`. Zeitpunkte kommen als ISO-Strings.
- Die Route muss vor `GET /api/applications/{id}` registriert sein, damit `overview` nicht
  als ID gelesen wird.

## Frontend

- **Feature `inventory`:**
  - `model/overview.ts`: zod-Schema, Typen und die reinen Funktionen `summarizeOverview`
    (Kachelwerte), `filterOverview` und `sortOverview`.
  - `api/` erhält `listApplicationsOverview`, `hooks/` erhält `useApplicationsOverview`.
- **Query-Key:** `["applications", "overview"]`. Er liegt unter `queryKeys.applications`
  und wird so beim Anlegen und Löschen mit invalidiert. Neu laden muss die Übersicht
  außerdem nach Ende eines Scans, nach Statusänderungen an Funden, nach SBOM- oder
  Komponenten-Änderungen und nach dem GitHub-Abgleich. Das heißt: überall dort zusätzlich
  invalidieren, wo heute `["findings"]` invalidiert wird.
- **Komponenten:**
  - `inventory-page.tsx` holt die Daten (Container).
  - Neu und rein: `overview-tiles.tsx`, `overview-table.tsx` und `create-application-dialog.tsx`.
  - `application-list.tsx` entfällt.
  - Die Kachel-Optik orientiert sich an den vorhandenen KPI-Karten in `shared/components`.
- **Test-IDs:**
  - `inventory-card-tile-critical`, `inventory-card-tile-overdue`,
    `inventory-card-tile-sbom`, `inventory-card-tile-unscanned`
  - `inventory-list-overview`, `inventory-item-app-<id>` (bleibt als Zeile)
  - `inventory-btn-sort-<spalte>`, `inventory-btn-create-app`, `inventory-dialog-create-app`
  - `inventory-btn-reset-filter`, `inventory-text-empty`, `inventory-text-filter-empty`
- **Farben:** nur semantische Tokens, keine Änderung an `src/index.css`. Die Schweregrad-Zähler nutzen dieselben Klassen wie
  die vorhandenen Schweregrad-Badges.

## Tests

- Domain: `scan_state` mit allen drei Fällen und `is_sbom_stale` an der 30-Tage-Grenze.
- Use Case mit Fakes:
  - zwei Anwendungen mit Funden in verschiedenen Zuständen (offen, erledigt, überfällig)
  - eine ausgebaute Komponente: zählt nicht als Komponente, ihr offener Fund zählt mit
  - eine Anwendung ohne SBOM und ohne Scan
  - Die Zahlen stimmen mit `compute_deadlines` je Anwendung überein.
- API-Test: Form des JSON in camelCase, und `overview` wird nicht als ID gelesen.
- Frontend:
  - `summarizeOverview`, `filterOverview` und `sortOverview`, einschließlich Standard-Sortierung
  - Kachel-Klick filtert und ein zweiter Klick setzt zurück
  - Spalten-Klick sortiert und dreht die Richtung
  - Zeilen-Klick öffnet das Detail
  - Anlege-Dialog
  - Leerzustände

## Dem Builder überlassen

- Genaue Abstände, Kachel-Layout und Breakpoints im Rahmen des Haus-Themes.
- Wie die Repository-Methode für die neueste SBOM-Version heißt und aufgebaut ist.
- Ob die Sortierung „Gescannt“ und „SBOM“ als Zeitstempel oder als Rang umgesetzt wird,
  solange die Reihenfolge oben gilt.
