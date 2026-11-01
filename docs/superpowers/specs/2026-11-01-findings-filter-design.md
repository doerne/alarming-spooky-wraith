# Filter für die Schwachstellen-Tabellen – Design (kurz)

Stand: 2026-11-01 · Branch `CVEFetch` · Teil von Stufe 4 der Haupt-Spec (`2026-10-31-cve-radar-design.md` §5.6/§5.7).

## Absicht
Die Funde-Tabellen (Dashboard, CVE-Reiter einer Anwendung) lassen sich eingrenzen,
damit man das Relevante schnell findet.

## Ziele / Nicht-Ziele
- **Ziele:** Filter Schweregrad, Status, Anwendung, Ökosystem, Freitextsuche;
  „Filter zurücksetzen“; Anzeige „N von M Funden“.
- **Nicht-Ziele (später):** Sortierung nach anderen Spalten, Paginierung, KEV-Filter
  (keine Daten), Filter nach Kategorie, Filter in der URL speichern.
- **Anti-Ziel:** Kacheln und Diagramm springen beim Filtern mit.

## Vorgehen (Approaches)
- A) Filtern im Browser – sofort, ohne Backend-Änderung, lädt aber immer alles; Spec
  sieht API-Filter vor.
- **B) Filtern in der API** – *gewählt*. Spec-konform, skaliert, Logik im Use Case testbar.

## Entscheidungen des Nutzers
- Filter: Schweregrad, Status, Anwendung, Ökosystem, Freitext.
- Diagramm folgt den Filtern nicht. *Meine Festlegung:* Kacheln auch nicht – beide
  zeigen den Gesamtstand; nur die Tabelle wird gefiltert.
- Weg B.

## Verhalten
- `GET /api/cves` mit optionalen Query-Parametern (mehrfach angebbar, wo sinnvoll):
  `severity` (mehrfach; `kritisch|hoch|mittel|niedrig`), `status` (mehrfach;
  FindingStatus-Werte), `application_id` (einfach, besteht), `ecosystem` (mehrfach;
  OSV-Name, Sonderwert `none` = Komponenten ohne Ökosystem), `q` (Freitext).
- Werte desselben Filters: ODER; verschiedene Filter: UND.
- `q`: getrimmt, Groß-/Kleinschreibung egal, Treffer in Advisory-ID, CVE-ID, Titel
  oder Komponentenname. Leeres `q` = kein Filter.
- Antwort wie bisher `{ items, total }`; `total` = Anzahl nach Filter.
  *Meine Festlegung:* zusätzlich `unfiltered_total` für „N von M“.
- Unbekannter Enum-Wert → 422 (FastAPI-Validierung).
- Sortierung bleibt Risk Score absteigend.

## Frontend
- Filterleiste über der Tabelle (shadcn-Komponenten; vorher suchen, was es gibt –
  z. B. `toggle-group`/`popover`+`checkbox` für Mehrfachauswahl, `select`, `input`).
- Freitext mit ~300 ms Verzögerung; andere Filter sofort.
- Filterzustand lebt in der Seite (`cves-page.tsx` bzw. Inventar-Detailseite), nicht in der URL.
- Kacheln/Diagramm: eigene ungefilterte Abfrage (bisheriges `useFindings()`),
  Tabelle: `useFindings(filters)` mit eigenem Query-Key.
- Inventar-CVE-Reiter: dieselbe Filterleiste ohne Anwendungsfilter.
- Leeres Ergebnis: Hinweis „Keine Funde für diese Filter“ mit Zurücksetzen.
- Filterleiste als reine Komponente im Feature `cves`; das Inventar darf sie nicht
  importieren → wiederverwendbare Teile ohne Fachlogik nach `shared/components/`,
  fachliche Werte (Stufen, Status) je Feature. *Builder wählt den regelkonformen Schnitt.*

## Tests
Use Case (jede Filterart, Kombination UND/ODER, `q` case-insensitive, `none`-Ökosystem),
API (Parameter, 422 bei unbekanntem Wert, `unfilteredTotal`), Vitest (Filterleiste,
Zurücksetzen, Anzeige „N von M“, leerer Zustand), `make check` grün.
