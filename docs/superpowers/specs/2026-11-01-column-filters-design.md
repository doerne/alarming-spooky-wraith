# Filter in den Spaltenüberschriften – Design (kurz)

Stand: 2026-11-01 · ersetzt die Filterleiste aus `2026-11-01-findings-filter-design.md`.

## Absicht
Die Spaltenüberschriften der Funde-Tabellen *sind* die Filter; die Filterleiste über der
Tabelle entfällt. Neue Spalte **Ökosystem**.

## Entscheidungen des Nutzers
| Spalte | Filter in der Überschrift |
|---|---|
| Risiko | Auswahlliste mit Häkchen (Kritisch, Hoch, Mittel, Niedrig) |
| Advisory | Suchfeld (CVE-ID/Advisory-ID oder Titel) |
| Anwendung | Auswahlliste mit Häkchen + Suchfeld in der Liste (nur Dashboard) |
| Komponente | Suchfeld (Name) |
| Ökosystem (neu) | Auswahlliste mit Häkchen inkl. „ohne“ |
| Fix | kein Filter |
| Status | Auswahlliste mit Häkchen |

## Meine Festlegungen
- Aktiver Filter: Filter-Symbol hervorgehoben + Anzahl gewählter Werte.
- Über der Tabelle nur „N von M Funden“ + „Filter zurücksetzen“.
- Bei 0 Treffern bleibt die Tabelle (mit ihren Filtern) sichtbar; Hinweis + Zurücksetzen als
  Zeile im Tabellenkörper.
- Keine neue Abhängigkeit: shadcn `popover` (radix-ui) + vorhandene `checkbox`/`input`; kein `cmdk`.
- Backend: Suche getrennt nach `advisory` (ID, CVE-ID, Titel) und `component` (Name);
  Anwendungsfilter mehrfach (`application`); `application_id` bleibt Scope fürs Inventar;
  `q` entfällt im Frontend (API darf ihn behalten).
- Suchfelder mit 300 ms Verzögerung; Kacheln/Diagramm weiter ungefiltert.
- Inventar: dieselben Spaltenfilter ohne Anwendung.

## Tests
Use Case/API für neue Parameter; Vitest für Kopf-Filter (Auswahl, Suche in Liste, Zähler,
Löschen), Tabellen mit Ökosystem-Spalte, leere Zeile mit Zurücksetzen; App-Test Dashboard.
